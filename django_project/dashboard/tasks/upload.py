from celery import shared_task
from celery.utils.log import get_task_logger

from dashboard.models import (
    LayerUploadSession, ERROR, DONE
)
from georepo.models import EntityType
from georepo.utils import load_layer_file
from georepo.utils.module_import import module_function

logger = get_task_logger(__name__)


@shared_task(name="process_layer_upload_session")
def process_layer_upload_session(layer_upload_session_id: str):

    layer_upload_session = LayerUploadSession.objects.get(
        id=layer_upload_session_id
    )
    for layer_file in layer_upload_session.layerfile_set.all().order_by(
            'level'):
        entity_type = EntityType.objects.get_by_label(
            layer_file.entity_type
        )
        name_format = ''
        id_format = ''
        try:
            name_format = layer_file.name_fields['format']
            id_format = layer_file.id_fields['format']
        except KeyError:
            pass
        loaded, message = load_layer_file(
            layer_file.layer_type,
            layer_file.layer_file.path,
            int(layer_file.level),
            entity_type,
            name_format,
            layer_upload_session.dataset.label,
            id_format,
            layer_upload_session.id
        )
        if loaded:
            layer_file.processed = True
            layer_file.save()
        else:
            layer_upload_session = (
                LayerUploadSession.objects.get(id=layer_upload_session.id)
            )
            layer_upload_session.status = ERROR
            layer_upload_session.message = message
            layer_upload_session.save()
            return
    layer_upload_session = (
        LayerUploadSession.objects.get(id=layer_upload_session.id)
    )
    layer_upload_session.status = DONE
    layer_upload_session.save()


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
    prepare_review = module_function(
        dataset.module.code_name,
        'prepare_review',
        'prepare_review')
    prepare_review(entity_upload)
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
