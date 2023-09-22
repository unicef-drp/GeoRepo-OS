from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from core.celery import app
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models import (
    LayerUploadSession, LayerUploadSessionActionLog,
    UPLOAD_PROCESS_COUNTRIES_SELECTION
)
from dashboard.tasks import (
    layer_upload_preprocessing,
    process_country_selection
)
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
            'country': <geographicalEntity.label|name_field>,
            'upload_id': <entity upload id (if exists)>,
            'admin_level_names': [dict of level+admin level name]
        }]
    }
    """

    def post(self, request, format=None):
        upload_session = request.data.get('upload_session', None)
        entities = request.data.get('entities', None)

        if not upload_session or not entities:
            raise Http404()

        upload_session = LayerUploadSession.objects.get(
            id=upload_session
        )
        if upload_session.is_read_only():
            return Response(status=200, data={
                'action_uuid': None
            })
        existing_uploads = upload_session.entityuploadstatus_set.exclude(
            status=''
        )
        # skip if already has existing_uploads
        if existing_uploads.exists():
            return Response(status=200, data={
                'action_uuid': None
            })
        action_data = {
            'entities': entities
        }
        session_action = LayerUploadSessionActionLog.objects.create(
            session=upload_session,
            action=UPLOAD_PROCESS_COUNTRIES_SELECTION,
            data=action_data
        )
        upload_session.current_process = UPLOAD_PROCESS_COUNTRIES_SELECTION
        upload_session.current_process_uuid = session_action.uuid
        upload_session.save(update_fields=['current_process',
                                           'current_process_uuid'])
        # trigger task
        task_obj = process_country_selection.delay(session_action.id)
        session_action.task_id = task_obj.id
        session_action.save(update_fields=['task_id'])
        return Response(status=200, data={
            'action_uuid': str(session_action.uuid)
        })


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
                layer_upload_session=upload_session,
                entity_upload_status__isnull=True
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
            task_id = layer_upload_preprocessing.delay(
                upload_session.id,
                upload_log.id
            )
            upload_session.task_id = task_id
            upload_session.save(update_fields=['task_id'])
        return Response(status=200)
