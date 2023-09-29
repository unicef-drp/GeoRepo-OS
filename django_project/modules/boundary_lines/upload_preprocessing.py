import time
from typing import Tuple
from core.celery import app
from georepo.models.entity import GeographicalEntity
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PRE_PROCESSING, PENDING, CANCELED
)
from dashboard.models.entity_upload import (
    EntityUploadStatus, STARTED, EntityUploadStatusLog
)
from dashboard.models.layer_file import LayerFile
from georepo.tasks import validate_ready_uploads


def is_valid_upload_session(
        upload_session: LayerUploadSession, **kwargs) -> Tuple[bool, str]:
    """
    do pre-validation before layer upload pre-processing/prepare_validation
    Returns: IsValid, ErrorMessage
    """
    return True, None


def prepare_validation(
    upload_session: LayerUploadSession,
    **kwargs):
    """
    Prepare validation at step 3
    - Create EntityUploadStatus object
    """
    start = time.time()
    # remove existing entity uploads
    uploads = upload_session.entityuploadstatus_set.all()
    uploads.delete()
    layer_files = LayerFile.objects.filter(
        layer_upload_session=upload_session
    )
    GeographicalEntity.objects.filter(
        layer_file__in=layer_files
    ).delete()
    # set status to PRE_PROCESSING
    upload_session.status = PRE_PROCESSING
    upload_session.save(update_fields=['status'])
    # create entity upload status with STARTED
    entity_upload_status = EntityUploadStatus.objects.create(
        upload_session=upload_session,
        status=STARTED,
        revised_entity_name=(
            upload_session.description[:300] if
            upload_session.description else 'Boundary Lines'
        )
    )
    # set status back to Pending
    upload_session.status = PENDING
    upload_session.auto_matched_parent_ready = True
    upload_session.save(update_fields=['status', 'auto_matched_parent_ready'])
    # trigger validation task
    upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
        layer_upload_session=upload_session,
        entity_upload_status__isnull=True
    )
    upload_log_entity, _ = EntityUploadStatusLog.objects.get_or_create(
        entity_upload_status=entity_upload_status,
        parent_log=upload_log
    )
    task = validate_ready_uploads.apply_async(
        (
            entity_upload_status.id,
            upload_log_entity.id
        ),
        queue='validation'
    )
    entity_upload_status.task_id = task.id
    entity_upload_status.save(update_fields=['task_id'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'boundary_lines.upload_preprocessing.prepare_validation',
            end - start
        )


def reset_preprocessing(
    upload_session: LayerUploadSession,
    **kwargs):
    """
    Remove entity uploads
    """
    start = time.time()
    if upload_session.task_id:
        # if there is task_id then stop it first
        app.control.revoke(
            upload_session.task_id,
            terminate=True,
            signal='SIGKILL'
        )
    uploads = upload_session.entityuploadstatus_set.all()
    uploads.delete()
    upload_session.auto_matched_parent_ready = False
    if upload_session.status != CANCELED:
        upload_session.status = PENDING
    upload_session.current_process = None
    upload_session.current_process_uuid = None
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status',
                                       'current_process',
                                       'current_process_uuid'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'boundary_lines.upload_preprocessing.reset_preprocessing',
            end - start
        )
