from celery import shared_task
import logging
from datetime import datetime
from django.contrib.auth import get_user_model
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    REVIEWING
)
from dashboard.models.batch_review import BatchReview, PROCESSING, DONE
from georepo.models.dataset import Dataset
from georepo.utils.module_import import module_function
from georepo.utils.dataset_view import trigger_generate_dynamic_views
from dashboard.models.notification import (
    Notification,
    NOTIF_TYPE_BATCH_REVIEW
)
from georepo.tasks.dataset_view import check_affected_dataset_views

logger = logging.getLogger(__name__)
UserModel = get_user_model()


@shared_task(name="review_approval")
def review_approval(entity_upload_id, user_id):
    """Run approval process for entity upload."""
    logger.info(f'Running review_approval {entity_upload_id}')
    entity_upload = EntityUploadStatus.objects.get(id=entity_upload_id)
    user = UserModel.objects.get(id=user_id)
    dataset = entity_upload.upload_session.dataset
    approve_revision = module_function(
        dataset.module.code_name,
        'review',
        'approve_revision'
    )
    approve_revision(entity_upload, user)
    check_affected_dataset_views.delay(
        entity_id=entity_upload.revised_geographical_entity.id
    )
    # remove task id
    entity_upload = EntityUploadStatus.objects.get(id=entity_upload_id)
    entity_upload.task_id = ''
    entity_upload.save(update_fields=['task_id'])
    logger.info(
        f'Review approval for {entity_upload_id} is finished.')


@shared_task(name="process_batch_review")
def process_batch_review(batch_review_id):
    """Process batch review."""
    logger.info(f'Running process_batch_review {batch_review_id}')
    batch_review = BatchReview.objects.get(id=batch_review_id)
    batch_review.started_at = datetime.now()
    batch_review.status = PROCESSING
    batch_review.progress = (
        f'Processing 0/'
        f'{len(batch_review.upload_ids)}'
    )
    batch_review.save(update_fields=['started_at', 'status', 'progress'])

    # dataset_list for generating vector tiles at last step
    dataset_list = {}
    # process approval/rejection
    item_processed = 0
    for upload_id in batch_review.upload_ids:
        upload = EntityUploadStatus.objects.filter(id=upload_id).first()
        if not upload:
            item_processed += 1
            continue
        upload_session = upload.upload_session
        dataset = upload_session.dataset
        # append dataset_id to dataset_list
        adm0_code = (
            upload.revised_geographical_entity.unique_code if
            upload.revised_geographical_entity else upload.revised_entity_id
        )
        if dataset.id in dataset_list:
            dataset_list[dataset.id].append(adm0_code)
        else:
            dataset_list[dataset.id] = [adm0_code]
        # check for upload.status == REVIEWING
        if upload.status != REVIEWING:
            item_processed += 1
            continue
        # check if boundary matching is available
        if not upload.comparison_data_ready:
            item_processed += 1
            continue
        if batch_review.is_approve:
            approve_func = module_function(
                dataset.module.code_name,
                'review',
                'approve_revision'
            )
            approve_func(upload, batch_review.review_by, True)
        else:
            reject_func = module_function(
                dataset.module.code_name,
                'review',
                'reject_revision'
            )
            reject_func(upload)
        updated_upload = EntityUploadStatus.objects.get(id=upload_id)
        updated_upload.task_id = ''
        updated_upload.save(update_fields=['task_id'])
        item_processed += 1
        batch_review.progress = (
            f'Processing {item_processed}/{len(batch_review.upload_ids)}'
        )
        batch_review.processed_ids.append(upload_id)
        batch_review.save(update_fields=['progress', 'processed_ids'])
    if batch_review.is_approve:
        # trigger generate dynamic views for dataset in upload_ids
        logger.info(
            f'Trigger vector tiles from batch_review {batch_review_id} - '
            f'with total dataset {len(dataset_list)}'
        )
        for dataset_id in dataset_list:
            adm0_list = dataset_list[dataset_id]
            dataset = Dataset.objects.filter(id=dataset_id).first()
            if not dataset:
                continue

            dataset.is_simplified = False
            dataset.save()
            trigger_generate_dynamic_views(dataset, adm0_list=adm0_list)
            check_affected_dataset_views.delay(unique_codes=adm0_list)
    # finished processing
    logger.info(f'Finished process_batch_review {batch_review_id}')
    batch_review.finished_at = datetime.now()
    batch_review.status = DONE
    batch_review.task_id = ''
    batch_review.progress = (
        f'Finished {len(batch_review.upload_ids)}/'
        f'{len(batch_review.upload_ids)}'
    )
    batch_review.save(update_fields=['finished_at', 'status',
                                     'progress', 'task_id'])
    # send notification
    message = (
        'System has finished processing your batch review!'
    )
    payload = {
        'severity': 'success'
    }

    Notification.objects.create(
        type=NOTIF_TYPE_BATCH_REVIEW,
        message=message,
        recipient=batch_review.review_by,
        payload=payload
    )
