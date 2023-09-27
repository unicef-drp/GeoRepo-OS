import time
from celery import shared_task
import logging
from django.db import transaction, OperationalError, DatabaseError
from django.db.models import Q
from django.utils import timezone
from dashboard.models.entity_upload import EntityUploadStatusLog

logger = logging.getLogger(__name__)


def find_entity_upload(upload_qs, status, update_status, task_id):
    """Find and lock entity upload status for processing."""
    upload = None
    with transaction.atomic():
        try:
            upload = upload_qs.select_for_update(nowait=True).get()
        except OperationalError:
            pass
        except DatabaseError:
            pass
        if upload and upload.status == status:
            upload.status = update_status
            upload.task_id = task_id
            upload.save(update_fields=['status', 'task_id'])
        else:
            upload = None
    return upload


@shared_task(name="validate_ready_uploads")
def validate_ready_uploads(entity_upload_id, log_obj_id=None):
    from dashboard.models.entity_upload import (
        EntityUploadStatus,
        STARTED,
        PROCESSING
    )
    from georepo.validation.layer_validation import (
        validate_layer_file
    )
    from dashboard.models.notification import (
        Notification,
        NOTIF_TYPE_LAYER_VALIDATION
    )
    start = time.time()
    upload_log = None
    if log_obj_id:
        upload_log = EntityUploadStatusLog.objects.get(id=log_obj_id)
    entity_upload = EntityUploadStatus.objects.get(
        id=entity_upload_id
    )
    if entity_upload.status != STARTED:
        logger.warning(
            f'upload {entity_upload_id} has invalid status: '
            f'{entity_upload.status}'
        )
        return

    if entity_upload.revised_entity_id:
        print('Validating {}'.format(entity_upload.revised_entity_id))
    else:
        print('Validating {}'.format(
            entity_upload.original_geographical_entity))
    entity_upload.status = PROCESSING
    entity_upload.started_at = timezone.now()
    entity_upload.save(update_fields=['status', 'started_at'])

    validate_layer_file(
        entity_upload,
        **{'log_object': upload_log}
    )

    # send notifications only when all upload have finished
    has_pending_upload = EntityUploadStatus.objects.filter(
        upload_session=entity_upload.upload_session
    ).filter(
        Q(status=STARTED) | Q(status=PROCESSING)
    ).exists()
    if not has_pending_upload:
        message = (
            'Your layer validation for '
            f'{entity_upload.upload_session.source}'
            ' has finished! Click here to view!'
        )
        payload = {
            'module': '',
            'session': entity_upload.upload_session.id,
            'dataset': entity_upload.upload_session.dataset.id,
            'step': 4,
            'severity': 'success'
        }
        if (entity_upload.upload_session.dataset and
                entity_upload.upload_session.dataset.module):
            payload['module'] = (
                entity_upload.upload_session
                .dataset.module.name
                .lower()
                .replace(' ', '_')
            )

        Notification.objects.create(
            type=NOTIF_TYPE_LAYER_VALIDATION,
            message=message,
            recipient=entity_upload.upload_session.uploader,
            payload=payload
        )

    end = time.time()
    if upload_log:
        upload_log.add_log(
            'ValidateUploadSession.validate_selected_country',
            end - start)
