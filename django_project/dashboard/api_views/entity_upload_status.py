from django.db import connection
import json
from collections import OrderedDict
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.models.entity import GeographicalEntity
from georepo.models.dataset import DatasetAdminLevelName
from dashboard.models import LayerUploadSession, EntityUploadStatus, \
    EntityUploadChildLv1
from dashboard.serializers.upload_session import DetailUploadSessionSerializer
from georepo.utils.module_import import module_function
from dashboard.api_views.common import EntityUploadStatusReadPermission


class EntityUploadStatusDetail(AzureAuthRequiredMixin,
                               EntityUploadStatusReadPermission, APIView):
    """
    Get detail of entity upload status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=id
        )
        upload_session_data = DetailUploadSessionSerializer(
            entity_upload.upload_session,
            many=False,
            context={
                'max_level': entity_upload.max_level,
                'revised_entity': entity_upload.revised_geographical_entity,
                'revision_number': entity_upload.revision_number
            }
        ).data
        upload_session_data['comparison_ready'] = (
            entity_upload.comparison_data_ready is not None and
            entity_upload.comparison_data_ready is True
        )
        upload_session_data['upload_status'] = entity_upload.status
        upload_session_data['progress'] = entity_upload.progress
        upload_session_data['adm0_entity'] = (
            entity_upload.revised_geographical_entity.label if
            entity_upload.revised_geographical_entity else
            entity_upload.revised_entity_name
        )
        return Response(upload_session_data)


class EntityUploadStatusList(AzureAuthRequiredMixin, APIView):

    def sort_error_summaries(self, summaries):
        if not summaries:
            return summaries
        result = []
        for summary in summaries:
            sorted = OrderedDict()
            if 'Level' in summary.keys():
                sorted['Level'] = summary['Level']
            if 'Entity' in summary.keys():
                sorted['Entity'] = summary['Entity']
            for key in summary.keys():
                if key not in ['Level', 'Entity']:
                    sorted[key] = summary[key]
            result.append(sorted)
        return result

    def get(self, request, *args, **kwargs):
        upload_session_id = request.GET.get('id', None)
        upload_session = LayerUploadSession.objects.get(
            id=upload_session_id
        )
        dataset = upload_session.dataset
        entity_uploads = (
            upload_session.entityuploadstatus_set.all()
        )
        entity_uploads = entity_uploads.exclude(
            status=''
        ).order_by('id')
        level_name_0 = DatasetAdminLevelName.objects.filter(
            dataset=dataset,
            level=0
        ).first()
        response_data = []
        for entity_upload in entity_uploads:
            entity = (
                entity_upload.revised_geographical_entity if
                entity_upload.revised_geographical_entity else
                entity_upload.original_geographical_entity
            )
            level_name = level_name_0.label if level_name_0 else 'Adm0'
            is_importable_func = module_function(
                dataset.module.code_name,
                'qc_validation',
                'is_validation_result_importable')
            is_importable, is_warning = is_importable_func(
                entity_upload,
                request.user
            )
            response_data.append({
                'id': entity_upload.id,
                level_name: (
                    entity.label
                    if entity
                    else entity_upload.revised_entity_name
                ),
                'started at': entity_upload.upload_session.started_at.strftime(
                    "%d %B %Y %H:%M:%S"),
                'status': entity_upload.status,
                'error_summaries': self.sort_error_summaries(
                    entity_upload.summaries),
                'error_report': (
                    entity_upload.error_report.url if
                    entity_upload.error_report else ''
                ),
                'is_importable': is_importable,
                'is_warning': is_warning,
                'progress': entity_upload.progress
            })

        return Response(
            status=200,
            data={
                'results': response_data,
                'is_read_only': upload_session.is_read_only()
            }
        )


class Level1UploadSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    default_code = serializers.SerializerMethodField()
    old_parent = serializers.SerializerMethodField()
    new_parent = serializers.SerializerMethodField()
    is_rematched = serializers.SerializerMethodField()
    overlap = serializers.SerializerMethodField()

    def get_label(self, obj: EntityUploadChildLv1):
        return obj.entity_name

    def get_default_code(self, obj: EntityUploadChildLv1):
        return obj.entity_id

    def get_old_parent(self, obj: EntityUploadChildLv1):
        return obj.parent_entity_id

    def get_new_parent(self, obj: EntityUploadChildLv1):
        if 'upload' in self.context:
            entity_upload = self.context['upload']
            if entity_upload.original_geographical_entity:
                return (
                    entity_upload.original_geographical_entity.internal_code
                )
            return entity_upload.revised_entity_id
        return '-'

    def get_is_rematched(self, obj: EntityUploadChildLv1):
        return 'Yes' if obj.is_parent_rematched else 'No'

    def get_overlap(self, obj: EntityUploadChildLv1):
        d = (
            round(obj.overlap_percentage, 2)
            if obj.overlap_percentage
            else 0
        )
        return d

    class Meta:
        model = EntityUploadChildLv1
        fields = [
            'id',
            'label',
            'default_code',
            'old_parent',
            'new_parent',
            'is_rematched',
            'overlap'
        ]


class EntityUploadLevel1List(AzureAuthRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        entity_upload_id = request.GET.get('id', None)
        entity_upload = EntityUploadStatus.objects.get(
            id=entity_upload_id
        )
        level1 = EntityUploadChildLv1.objects.filter(
            entity_upload=entity_upload
        ).order_by('overlap_percentage')
        return Response(
            status=200,
            data=Level1UploadSerializer(
                level1,
                many=True,
                context={
                    'upload': entity_upload
                }
            ).data
        )


class OverlapsEntitySerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    id_1 = serializers.SerializerMethodField()
    label_1 = serializers.SerializerMethodField()
    default_code_1 = serializers.SerializerMethodField()
    id_2 = serializers.SerializerMethodField()
    label_2 = serializers.SerializerMethodField()
    default_code_2 = serializers.SerializerMethodField()
    overlaps_percentage = serializers.SerializerMethodField()
    overlaps_area = serializers.SerializerMethodField()

    def get_level(self, obj):
        return obj.get('level', '')

    def get_id_1(self, obj):
        return obj.get('geo1_id', '')

    def get_label_1(self, obj):
        return obj.get('geo1_label', '')

    def get_default_code_1(self, obj):
        return obj.get('geo1_code', '')

    def get_id_2(self, obj):
        return obj.get('geo2_id', '')

    def get_label_2(self, obj):
        return obj.get('geo2_label', '')

    def get_default_code_2(self, obj):
        return obj.get('geo2_code', '')

    def get_overlaps_percentage(self, obj):
        overlaps = obj.get('percentage', 0)
        return f'{overlaps:.2f}'

    def get_overlaps_area(self, obj):
        overlaps = obj.get('overlaps_area', 0)
        if overlaps < 1e-4:
            return f'{overlaps:.8f} km²'
        return f'{overlaps:.4f} km²'

    class Meta:
        model = GeographicalEntity
        fields = [
            'level',
            'id_1',
            'label_1',
            'default_code_1',
            'id_2',
            'label_2',
            'default_code_2',
            'overlaps_percentage',
            'overlaps_area'
        ]


class OverlapsEntityUploadList(AzureAuthRequiredMixin, APIView):
    """
    Fetch overlaps entities in same level from EntityUpload
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        upload_id = kwargs.get('upload_id')
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=upload_id
        )
        ancestor = entity_upload.revised_geographical_entity
        level = request.GET.get('level', None)
        dataset = entity_upload.upload_session.dataset
        raw_sql = (
            'select gg_1.level as level, '
            'gg_1.id as geo1_id, gg_1.label as geo1_label, '
            'gg_1.internal_code as geo1_code, '
            'gg_2.id as geo2_id, gg_2.label as geo2_label, '
            'gg_2.internal_code as geo2_code, '
            'ST_AREA(ST_INTERSECTION(gg_1.geometry, gg_2.geometry), '
            ' true)/10^6 '
            'as overlaps_area, '
            '100*ST_AREA(ST_INTERSECTION(gg_1.geometry, gg_2.geometry),'
            ' true)/ST_AREA(gg_2.geometry, true) '
            'as percentage '
            'from georepo_geographicalentity gg_1 '
            'INNER JOIN georepo_geographicalentity gg_2 ON '
            '    gg_2.dataset_id=gg_1.dataset_id '
            '    AND gg_1.id <> gg_2.id and gg_1.level=gg_2.level '
            '    and gg_1.layer_file_id = gg_2.layer_file_id '
            '    AND ST_OVERLAPS(gg_1.geometry, gg_2.geometry) '
            'where gg_1.dataset_id=%s '
            'AND (gg_1.id=%s OR gg_1.ancestor_id=%s) '
        )
        query_values = [dataset.id,
                        ancestor.id, ancestor.id]
        if level is not None:
            raw_sql = (
                raw_sql + ' AND gg_1.level=%s'
            )
            query_values.append(level)
        results = {}
        with connection.cursor() as cursor:
            cursor.execute(raw_sql, query_values)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            for row in rows:
                data = dict(zip(columns, row))
                key = f'{min(row[1], row[4])}_{max(row[1], row[4])}'
                if key not in results:
                    results[key] = data
        return Response(
            status=200,
            data=OverlapsEntitySerializer(results.values(), many=True).data
        )


class OverlapsEntityUploadDetail(AzureAuthRequiredMixin, APIView):
    """
    Get the detail of overlaps area to be highlighted in map
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        entity_id_1 = kwargs.get('entity_id_1')
        entity_id_2 = kwargs.get('entity_id_2')
        entity_1 = get_object_or_404(
            GeographicalEntity,
            id=entity_id_1
        )
        entity_2 = get_object_or_404(
            GeographicalEntity,
            id=entity_id_2
        )
        union = (
            entity_1.geometry.union(entity_2.geometry)
        )
        bbox = union.extent
        overlaps = entity_1.geometry.intersection(
            entity_2.geometry
        )
        return Response(
            status=200,
            data={
                'geometry_1': (
                    json.loads(
                        entity_1.geometry.geojson
                    )
                ),
                'geometry_2': (
                    json.loads(
                        entity_2.geometry.geojson
                    )
                ),
                'bbox': bbox,
                'overlaps': (
                    json.loads(
                        overlaps.geojson
                    )
                )
            }
        )
