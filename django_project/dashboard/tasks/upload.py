from celery import shared_task
import logging
import time
from core.celery import app
from django.utils import timezone

from dashboard.models import (
    LayerUploadSession, EntityUploadStatusLog,
    STARTED,
    EntityUploadStatus,
    REVIEWING,
    LayerUploadSessionActionLog
)
from georepo.tasks import validate_ready_uploads
from georepo.utils.module_import import module_function

logger = logging.getLogger(__name__)


def validate_selected_country(upload_session, entities, **kwargs):
    start = time.time()
    country_ids = [
        entity_upload['country_entity_id'] for
        entity_upload in entities if entity_upload['country_entity_id']
    ]
    other_uploads = EntityUploadStatus.objects.filter(
        original_geographical_entity__id__in=country_ids,
        upload_session__dataset=upload_session.dataset,
        status=REVIEWING
    ).exclude(
        upload_session=upload_session
    )
    if other_uploads.exists():
        uploads = other_uploads[:3]
        other_countries = []
        for upload in uploads:
            if upload.original_geographical_entity:
                other_countries.append(
                    upload.original_geographical_entity.internal_code
                )
            elif upload.revised_entity_id:
                other_countries.append(
                    upload.revised_entity_id
                )
        return (
            False,
            f'There are {other_uploads.count()} countries '
            'has upload being reviewed: ' +
            ', '.join(other_countries)
        )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'ValidateUploadSession.validate_selected_country',
            end - start)
    return True, ''


@shared_task(name="process_country_selection")
def process_country_selection(session_action_id):
    """Run process country selection."""
    logger.info(f'Running process_country_selection {session_action_id}')
    action_data = LayerUploadSessionActionLog.objects.get(id=session_action_id)
    action_data.on_started()
    start = time.time()
    upload_session = action_data.session
    entities = action_data.data['entities']
    upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
        layer_upload_session=upload_session,
        entity_upload_status__isnull=True
    )
    is_selected_valid, error = validate_selected_country(
        upload_session,
        entities,
        **{'log_object': upload_log}
    )
    if not is_selected_valid:
        action_data.on_finished(True, {
            'is_valid': False,
            'error': error
        })
        return
    entity_upload_ids = []
    for entity_upload in entities:
        max_level = int(entity_upload['max_level'])
        layer0_id = entity_upload['layer0_id']
        country = entity_upload['country']
        if entity_upload['country_entity_id']:
            entity_upload_status, _ = (
                EntityUploadStatus.objects.update_or_create(
                    original_geographical_entity_id=(
                        entity_upload['country_entity_id']
                    ),
                    upload_session=upload_session,
                    defaults={
                        'status': STARTED,
                        'logs': '',
                        'max_level': max_level,
                        'started_at': timezone.now(),
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
                        'started_at': timezone.now(),
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
    action_data.on_finished(True, {
        'is_valid': True,
        'error': None
    })
    # update session step
    upload_session.last_step = 4
    upload_session.save(update_fields=['last_step'])


@shared_task(name='run_comparison_boundary')
def run_comparison_boundary(entity_upload_id: int):
    from dashboard.models.entity_upload import (
        EntityUploadStatus,
        REVIEWING
    )
    from dashboard.models.notification import (
        Notification,
        NOTIF_TYPE_BOUNDARY_MATCHING
    )
    entity_upload = EntityUploadStatus.objects.get(
        id=entity_upload_id
    )
    dataset = entity_upload.upload_session.dataset

    upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
        entity_upload_status=entity_upload,
        layer_upload_session=entity_upload.upload_session
    )
    prepare_review = module_function(
        dataset.module.code_name,
        'prepare_review',
        'prepare_review')
    prepare_review(
        entity_upload,
        **{'log_object': upload_log}
    )
    # send notifications only when all upload has been prepared
    has_pending_upload = EntityUploadStatus.objects.filter(
            upload_session=entity_upload.upload_session,
            status=REVIEWING,
            comparison_data_ready=False
    ).exists()
    if not has_pending_upload:
        message = (
            f'Boundary matching for {entity_upload.upload_session.source}'
            ' has finished! Click here to view!'
        )
        payload = {
            'review_id': entity_upload_id,
            'severity': 'success'
        }

        Notification.objects.create(
            type=NOTIF_TYPE_BOUNDARY_MATCHING,
            message=message,
            recipient=entity_upload.upload_session.uploader,
            payload=payload
        )


@shared_task(name='layer_upload_preprocessing')
def layer_upload_preprocessing(upload_session_id: int):
    logger.info(
        'Running layer_upload_preprocessing '
        f'for session {upload_session_id}'
    )
    upload_session = LayerUploadSession.objects.get(
        id=upload_session_id
    )
    dataset = upload_session.dataset
    prepare_validation = module_function(
        dataset.module.code_name,
        'upload_preprocessing',
        'prepare_validation')
    prepare_validation(upload_session)
