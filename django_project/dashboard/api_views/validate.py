import time
from datetime import datetime
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from core.celery import app
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models import (
    LayerUploadSession, STARTED,
    EntityUploadStatus
)
from dashboard.models.entity_upload import (
    REVIEWING as UPLOAD_REVIEWING
)
from georepo.models import GeographicalEntity
from georepo.tasks import validate_ready_uploads
from dashboard.tasks import layer_upload_preprocessing
from dashboard.models.entity_upload import EntityUploadStatusLog
from georepo.utils.module_import import module_function


class ValidateUploadSession(AzureAuthRequiredMixin, APIView):
    """
    Example request body:
    {
        'upload_session': 123,
        'entities': [{
            'id': <geographicalEntity.id|uuid>,
            'layer0_id': <default_code>,
            'country_entity_id': <geographicalEntity.id>,
            'max_level': <selected max level to be imported>,
            'country': <geographicalEntity.label|name_field>
        }]
    }
    """

    def validate_selected_country(self, upload_session, entities, **kwargs):
        start = time.time()
        for entity_upload in entities:
            country = entity_upload['country']
            if entity_upload['country_entity_id']:
                other_uploads = EntityUploadStatus.objects.filter(
                    original_geographical_entity__id=(
                        entity_upload['country_entity_id']
                    ),
                    upload_session__dataset=upload_session.dataset,
                    status=UPLOAD_REVIEWING
                ).exclude(
                    upload_session=upload_session
                )
                if other_uploads.exists():
                    return False, f'{country} has upload being reviewed'
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'ValidateUploadSession.validate_selected_country',
                end - start)
        return True, ''

    def post(self, request, format=None):
        start = time.time()
        upload_session = request.data.get('upload_session', None)
        entities = request.data.get('entities', None)

        if not upload_session or not entities:
            raise Http404()

        upload_session = LayerUploadSession.objects.get(
            id=upload_session
        )
        upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
            layer_upload_session=upload_session
        )
        if upload_session.is_read_only():
            return Response(status=200)
        existing_uploads = upload_session.entityuploadstatus_set.exclude(
            status=''
        )
        # skip if already has existing_uploads
        if existing_uploads.exists():
            return Response(status=200)
        is_selected_valid, error = self.validate_selected_country(
            upload_session,
            entities,
            **{'log_object': upload_log}
        )
        if not is_selected_valid:
            return Response(status=400, data={
                        'detail': error
                    })
        entity_upload_ids = []
        for entity_upload in entities:
            max_level = int(entity_upload['max_level'])
            layer0_id = entity_upload['layer0_id']
            country = entity_upload['country']
            if entity_upload['country_entity_id']:
                geographical_entity = GeographicalEntity.objects.get(
                    id=entity_upload['country_entity_id']
                )
                entity_upload_status, _ = (
                    EntityUploadStatus.objects.update_or_create(
                        original_geographical_entity=geographical_entity,
                        upload_session=upload_session,
                        defaults={
                            'status': STARTED,
                            'logs': '',
                            'max_level': max_level,
                            'started_at': datetime.now(),
                            'summaries': None,
                            'error_report': None,
                            'admin_level_names': (
                                entity_upload['admin_level_names']
                            )
                        }
                    )
                )
                entity_upload_ids.append(entity_upload_status.id)
            else:
                entity_upload_status, _ = (
                    EntityUploadStatus.objects.update_or_create(
                        revised_entity_id=layer0_id,
                        revised_entity_name=country,
                        upload_session=upload_session,
                        defaults={
                            'status': STARTED,
                            'logs': '',
                            'max_level': max_level,
                            'started_at': datetime.now(),
                            'summaries': None,
                            'error_report': None,
                            'admin_level_names': (
                                entity_upload['admin_level_names']
                            )
                        }
                    )
                )
                entity_upload_ids.append(entity_upload_status.id)
            if entity_upload_status.task_id:
                app.control.revoke(
                    entity_upload_status.task_id,
                    terminate=True,
                    signal='SIGKILL'
                )
            upload_log_entity, _ = EntityUploadStatusLog.objects.get_or_create(
                entity_upload_status=entity_upload_status,
                parent_log=upload_log
            )
            # trigger validation task
            task = validate_ready_uploads.apply_async(
                (
                    entity_upload_status.id,
                    upload_log_entity.id
                ),
                queue='validation'
            )
            entity_upload_status.task_id = task.id
            entity_upload_status.save(update_fields=['task_id'])
        # delete/reset the other entity uploads
        other_uploads = EntityUploadStatus.objects.filter(
            upload_session=upload_session
        ).exclude(id__in=entity_upload_ids)
        for upload in other_uploads:
            upload.status = ''
            upload.logs = ''
            upload.max_level = ''
            upload.summaries = None
            revised = None
            if upload.revised_geographical_entity:
                revised = upload.revised_geographical_entity
                upload.revised_geographical_entity = None
            if upload.error_report:
                upload.error_report.delete(save=False)
                upload.error_report = None
            if upload.task_id:
                app.control.revoke(
                    upload.task_id,
                    terminate=True,
                    signal='SIGKILL'
                )
                upload.task_id = ''
            upload.save()
            # this will removed entities from non-selected upload
            if revised:
                revised.delete()

        end = time.time()
        upload_log.add_log('ValidateUploadSession.post', end - start)
        return Response(status=200)


class LayerUploadPreprocess(AzureAuthRequiredMixin, APIView):
    """
    Triggered after step 3
        if it is layer file 0, then validate duplicate
    Triggered pre-processing bg task
    """

    def post(self, request, format=None):
        upload_session_id = request.data.get('upload_session', None)
        if not upload_session_id:
            raise Http404()
        upload_session = LayerUploadSession.objects.get(
            id=upload_session_id
        )
        if upload_session.is_read_only():
            return Response(status=200)
        dataset = upload_session.dataset
        if (
            not upload_session.auto_matched_parent_ready and
            not upload_session.is_in_progress()
        ):
            upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
                layer_upload_session=upload_session
            )

            pre_validation = module_function(
                dataset.module.code_name,
                'upload_preprocessing',
                'is_valid_upload_session')
            is_valid, error_message = pre_validation(
                upload_session,
                **{'log_object': upload_log}
            )
            if not is_valid:
                return Response(status=400, data={
                    'detail': error_message
                })
            # if there is task_id then stop it first
            app.control.revoke(
                upload_session.task_id,
                terminate=True,
                signal='SIGKILL'
            )
            task_id = layer_upload_preprocessing.delay(upload_session.id)
            upload_session.task_id = task_id
            upload_session.save(update_fields=['task_id'])
        return Response(status=200)
