import time
from typing import Tuple
from core.celery import app
from georepo.models.entity import GeographicalEntity
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PRE_PROCESSING, PENDING
)
from dashboard.models.entity_upload import EntityUploadStatus, STARTED
from dashboard.models.layer_file import LayerFile


def is_valid_upload_session(
        upload_session: LayerUploadSession) -> Tuple[bool, str]:
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
    # create entity upload status with STARTED to trigger validation
    EntityUploadStatus.objects.create(
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
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.reset_preprocessing',
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
    upload_session.status = PENDING
    upload_session.current_process = None
    upload_session.current_process_uuid = None
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status',
                                       'current_process',
                                       'current_process_uuid'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.reset_preprocessing',
            end - start
        )
