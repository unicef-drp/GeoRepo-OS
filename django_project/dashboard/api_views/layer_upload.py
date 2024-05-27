import os
import logging
import traceback
from datetime import datetime
from django.db.models import IntegerField, Min
from django.db.models.functions import Cast
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.http import Http404, HttpResponseForbidden, FileResponse,\
    HttpResponseNotFound
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models import (
    LayerFile,
    LayerUploadSession, GEOJSON, SHAPEFILE, GEOPACKAGE
)
from dashboard.serializers.layer_uploads import LayerUploadSerializer
from georepo.models import EntityType
from georepo.utils.shapefile import (
    validate_shapefile_zip
)
from georepo.utils.layers import \
    validate_layer_file_metadata


logger = logging.getLogger(__name__)


class LayerProcessStatusView(APIView):
    def get(self, request):
        session_id = request.GET.get('session_id')
        if not session_id:
            return Response(status=404)
        try:
            upload_session = LayerUploadSession.objects.get(
                id=session_id
            )
        except LayerUploadSession.DoesNotExist:
            return Response(status=404)
        return Response(
            status=200,
            data={
                'status': upload_session.status,
                'progress': upload_session.progress,
                'message': upload_session.message
            }
        )


class LayerUploadView(AzureAuthRequiredMixin, APIView):
    parser_classes = (MultiPartParser,)

    def check_layer_type(self, filename: str) -> str:
        if (filename.lower().endswith('.geojson') or
                filename.lower().endswith('.json')):
            return GEOJSON
        elif filename.lower().endswith('.zip'):
            return SHAPEFILE
        elif filename.lower().endswith('.gpkg'):
            return GEOPACKAGE
        return ''

    def validate_shapefile_zip(self, file_obj: any) -> str:
        _, error = validate_shapefile_zip(file_obj)
        if error:
            return ('Missing required file(s) inside zip file: \n- ' +
                    '\n- '.join(error)
                    )
        return ''

    def remove_temp_file(self, file_obj: any) -> None:
        if isinstance(file_obj, TemporaryUploadedFile):
            if os.path.exists(file_obj.temporary_file_path()):
                os.remove(file_obj.temporary_file_path())

    def check_crs_type(self, file_obj: any, type: any):
        return validate_layer_file_metadata(
            file_obj,
            type
        )

    def post(self, request, format=None):
        file_obj = request.FILES['file']
        upload_session = request.data.get('uploadSession', '')
        level = request.data.get('level', '')
        layer_file = None
        try:
            layer_type = self.check_layer_type(file_obj.name)
            if layer_type == '':
                self.remove_temp_file(file_obj)
                return Response(
                    status=400,
                    data={
                        'detail': 'Unrecognized file type!'
                    }
                )
            if layer_type == SHAPEFILE:
                validate_shp_file = self.validate_shapefile_zip(file_obj)
                if validate_shp_file != '':
                    self.remove_temp_file(file_obj)
                    return Response(
                        status=400,
                        data={
                            'detail': validate_shp_file
                        }
                    )
            is_valid_crs, crs, feature_count, attrs = self.check_crs_type(
                file_obj, layer_type)
            if not is_valid_crs:
                self.remove_temp_file(file_obj)
                return Response(
                    status=400,
                    data={
                        'detail': f'Incorrect CRS type: {crs}!'
                    }
                )
            if upload_session:
                upload_session = LayerUploadSession.objects.get(
                    id=upload_session
                )
                if upload_session.is_read_only():
                    self.remove_temp_file(file_obj)
                    return Response(
                        status=400,
                        data={
                            'detail': 'Invalid Upload Session'
                        }
                    )
                layer_file, _ = LayerFile.objects.get_or_create(
                    meta_id=request.POST.get('id', ''),
                    uploader=self.request.user,
                    layer_upload_session=upload_session,
                    layer_type=layer_type,
                    defaults={
                        'name': file_obj.name,
                        'upload_date': datetime.now(),
                        'feature_count': feature_count,
                        'attributes': attrs
                    }
                )
            else:
                layer_file, _ = LayerFile.objects.get_or_create(
                    meta_id=request.POST.get('id', ''),
                    uploader=self.request.user,
                    layer_type=layer_type,
                    defaults={
                        'name': file_obj.name,
                        'upload_date': datetime.now(),
                        'feature_count': feature_count,
                        'attributes': attrs
                    }
                )
            if level:
                layer_file.level = level
            layer_file.layer_file = file_obj
            layer_file.save()
        except Exception as ex:
            logger.error('Failed uploading file!')
            logger.error(ex)
            logger.error(traceback.format_exc())
            # if fail to upload, remove the file
            if layer_file:
                layer_file.delete()
            return Response(
                status=400,
                data={
                    'detail': (
                        'There is unexpected error while uploading {}. '
                        'Please try again to reupload the file!'
                    ).format(file_obj.name if file_obj else 'the file')
                }
            )
        finally:
            self.remove_temp_file(file_obj)
        return Response(status=204)


class LayerRemoveView(AzureAuthRequiredMixin, APIView):
    def post(self, request, format=None):
        file_meta_id = request.data.get('meta_id')
        layer_file = LayerFile.objects.filter(
            meta_id=file_meta_id
        )
        if not layer_file.exists():
            return Response(status=200)
        layer_file_obj = layer_file.first()
        if layer_file_obj.layer_upload_session.is_read_only():
            return Response(
                status=400,
                data={
                    'detail': 'Invalid Upload Session'
                }
            )
        layer_uploads = LayerFile.objects.filter(
            layer_upload_session=layer_file_obj.layer_upload_session,
        ).exclude(id=layer_file_obj.id).order_by('level')
        # start at level from the first layer file
        level = LayerFile.objects.filter(
            layer_upload_session=layer_file_obj.layer_upload_session,
        ).annotate(
            level_int=Cast('level', IntegerField())
        ).aggregate(min_level=Min('level_int'))['min_level']
        # fix level ordering
        for layer_upload in layer_uploads:
            layer_upload.level = f'{level}'
            layer_upload.save(update_fields=['level'])
            level += 1
        layer_file_obj.delete()
        return Response(status=200)


class LayerUploadList(AzureAuthRequiredMixin, APIView):
    """
    Get list of layer_file by upload session
    """

    def get(self, request):
        upload_session_id = request.GET.get('upload_session')
        upload_session = LayerUploadSession.objects.get(
            id=upload_session_id
        )
        layer_uploads = LayerFile.objects.filter(
            layer_upload_session=upload_session
        ).order_by('level')
        serializer = LayerUploadSerializer(
            layer_uploads,
            many=True,
            context={
                'is_read_only': upload_session.is_read_only()
            }
        )
        return Response(
            serializer.data
        )


class UpdateLayerUpload(AzureAuthRequiredMixin, APIView):
    """
    Update layer_file object
    """

    def post(self, request, format=None):
        layer_upload = get_object_or_404(
            LayerFile,
            id=request.data.get('id', '')
        )
        if layer_upload.layer_upload_session.is_read_only():
            return Response(
                status=400,
                data={
                    'detail': 'Invalid Upload Session'
                }
            )
        location_type_field = request.data.get('location_type_field')
        parent_id_field = request.data.get('parent_id_field', '')
        source_field = request.data.get('source_field', '')
        name_fields = request.data.get('name_fields')
        id_fields = request.data.get('id_fields')
        entity_type = request.data.get('entity_type')
        boundary_type = request.data.get('boundary_type')
        privacy_level_field = request.data.get('privacy_level_field')
        privacy_level = request.data.get('privacy_level')

        if privacy_level_field:
            layer_upload.privacy_level_field = privacy_level_field
            layer_upload.privacy_level = ''
        if privacy_level:
            layer_upload.privacy_level = privacy_level
            layer_upload.privacy_level_field = ''
        if location_type_field:
            layer_upload.location_type_field = location_type_field
            layer_upload.entity_type = ''
        if entity_type:
            layer_upload.location_type_field = ''
            layer_upload.entity_type = entity_type
        layer_upload.parent_id_field = parent_id_field
        layer_upload.source_field = source_field
        if name_fields:
            layer_upload.name_fields = name_fields
        if id_fields:
            layer_upload.id_fields = id_fields
        if boundary_type:
            layer_upload.boundary_type = boundary_type
        layer_upload.save(update_fields=[
            'privacy_level_field', 'privacy_level',
            'location_type_field', 'entity_type',
            'parent_id_field', 'source_field',
            'name_fields', 'id_fields',
            'boundary_type'
        ])
        return Response(status=200, data=LayerUploadSerializer(
            layer_upload
        ).data)


class LayerFileAttributes(AzureAuthRequiredMixin, APIView):
    """
    Read layer_file and returns all the attributes
    """

    def get(self, request, format=None):
        layer_file_id = request.GET.get('id')
        layer_file = LayerFile.objects.get(
            id=layer_file_id
        )
        if not layer_file.layer_file:
            raise Http404('File is missing!')
        return Response(status=200, data=layer_file.attributes)


class LayerFileEntityTypeList(AzureAuthRequiredMixin, APIView):
    """
    Return distinct list of entity_type from LayerFile
    """

    def get(self, request, format=None):
        mode = request.query_params.get('mode', 'layer_file')
        if mode == 'all':
            entity_types = EntityType.objects.exclude(
                label=''
            ).order_by('label').values_list('label', flat=True).distinct()
        else:
            entity_types = LayerFile.objects.exclude(
                entity_type=''
            ).order_by('entity_type').values_list(
                'entity_type', flat=True).distinct()
        return Response(status=200, data=list(entity_types))


class LayerFileChangeLevel(AzureAuthRequiredMixin, APIView):
    """
    Update level of layer_file object
    Example payload:
    {
        'levels': {
             'id-file-1': '0',
             'id-file-2': '1'
         }
    }
    """

    def post(self, request, format=None):
        levels = request.data.get('levels', {})
        for meta_id, level in levels.items():
            layer_file = get_object_or_404(
                LayerFile,
                meta_id=meta_id
            )
            if layer_file.layer_upload_session.is_read_only():
                return Response(
                    status=400,
                    data={
                        'detail': 'Invalid Upload Session'
                    }
                )
            layer_file.level = level
            layer_file.save(update_fields=['level'])
        return Response(status=204)


class LayerFileDownload(UserPassesTestMixin, APIView):
    """
    API view to download uploaded layer file
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def handle_no_permission(self):
        if not self.layer_file.exists():
            return HttpResponseNotFound('File is missing!')
        return HttpResponseForbidden('No permission')

    def test_func(self):
        file_meta_id = self.request.GET.get('meta_id')
        self.layer_file = LayerFile.objects.filter(
            meta_id=file_meta_id
        )
        if not self.layer_file.exists():
            return False
        layer_file = self.layer_file.first()
        if self.request.user.is_superuser:
            return True
        if layer_file.layer_upload_session.uploader == self.request.user:
            return True
        return False

    def get(self, request, *args, **kwargs):
        layer_file = self.layer_file.first()
        if not layer_file.layer_file:
            return HttpResponseNotFound('File is missing!')
        return FileResponse(layer_file.layer_file, as_attachment=True)
