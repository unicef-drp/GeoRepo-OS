from celery import shared_task, states
import logging
from django.utils import timezone
from datetime import timedelta
from ast import literal_eval as make_tuple
from georepo.models import (
    BackgroundTask,
    DatasetViewResource,
    DatasetView,
    Dataset,
    ExportRequest,
    ExportRequestStatusText
)
from georepo.models.base_task_request import (
    ERROR
)
from georepo.utils.celery_helper import (
    get_task_status,
    TASK_NOT_FOUND,
    cancel_task
)
from georepo.utils.module_import import module_function


logger = logging.getLogger(__name__)
# remove tasks with two months old
REMOVE_AFTER_DAYS = 60


@shared_task(name="check_celery_background_tasks")
def check_celery_background_tasks():
    tasks = BackgroundTask.objects.filter(
        status__in=[
            BackgroundTask.BackgroundTaskStatus.QUEUED,
            BackgroundTask.BackgroundTaskStatus.RUNNING,
            BackgroundTask.BackgroundTaskStatus.STOPPED
        ],
    )
    for task in tasks:
        if task.status == BackgroundTask.BackgroundTaskStatus.STOPPED:
            # stopped/failure task needs to be handled manually
            # we just need to sync the status back to the resources
            handle_task_failure(task)
            continue
        if not task.is_possible_interrupted():
            continue
        try:
            # check using flower API
            status = get_task_status(task.task_id)
            if status not in [states.FAILURE, TASK_NOT_FOUND]:
                continue
            handle_task_with_status(task, status)
        except Exception as ex:
            logger.error(f'Failed to get_task_status task: {str(task)}')
            logger.error(ex)


def on_task_invalidated(task: BackgroundTask):
    cancel_task(task.task_id)
    task.status = BackgroundTask.BackgroundTaskStatus.INVALIDATED
    task.last_update = timezone.now()
    task.save(update_fields=['status', 'last_update'])


def handle_task_with_status(task: BackgroundTask, status: str):
    if status == states.FAILURE:
        try:
            handle_task_failure(task)
        except Exception as ex:
            logger.error(f'Failed to handle failure task: {str(task)}')
            logger.error(ex)
        finally:
            on_task_invalidated(task)
    elif status == TASK_NOT_FOUND:
        try:
            handle_task_interrupted(task)
        except Exception as ex:
            logger.error(f'Failed to handle interrupted task: {str(task)}')
            logger.error(ex)
        finally:
            on_task_invalidated(task)


def handle_task_failure(task: BackgroundTask):
    from dashboard.models import (
        EntityUploadStatus, PROCESSING_ERROR
    )
    task_name = task.name
    parameters = task.parameters
    task_param = make_tuple(parameters or '()')
    logger.info(f'Found failed task {task_name} with parameters {parameters}')
    if task_name == 'generate_view_resource_vector_tiles_task':
        # set status of view resource to failed
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter generate_view_resource_vector_tiles_task')
        try:
            view_resource_id = task_param[0]
            resource = DatasetViewResource.objects.filter(
                id=view_resource_id).first()
            if resource is None:
                return
            resource.status = DatasetView.DatasetViewStatus.ERROR
            resource.vector_tile_sync_status = (
                DatasetViewResource.SyncStatus.OUT_OF_SYNC
            )
            resource.tiling_current_task = None
            resource.save()
        except DatasetViewResource.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'view_vector_tiles_task':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter view_vector_tiles_task')
        try:
            view_id = task_param[0]
            view = DatasetView.objects.filter(id=view_id).first()
            if view is None:
                return
            view.status = DatasetView.DatasetViewStatus.ERROR
            has_custom_tiling_config = (
                view.datasetviewtilingconfig_set.all().exists()
            )
            if has_custom_tiling_config:
                view.simplification_progress = 'Simplification error'
                view.simplification_current_task = None
                view.simplification_sync_status = DatasetView.SyncStatus.ERROR
                view.save(update_fields=['status', 'simplification_progress',
                                         'simplification_current_task',
                                         'simplification_sync_status'])
            else:
                view.save(update_fields=['status'])
                # update dataset simplification status
                dataset = view.dataset
                dataset.simplification_progress = 'Simplification error'
                dataset.simplification_sync_status = Dataset.SyncStatus.ERROR
                dataset.is_simplified = False
                dataset.save(update_fields=['simplification_progress',
                                            'is_simplified',
                                            'simplification_sync_status'])
        except DatasetView.DoesNotExist as ex:
            logger.error(ex)
    elif (
        task_name == 'validate_ready_uploads' or
        task_name == 'run_comparison_boundary'
    ):
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter validate_ready_uploads')
        try:
            upload_id = task_param[0]
            upload = EntityUploadStatus.objects.filter(id=upload_id).first()
            if upload is None:
                return
            upload.status = PROCESSING_ERROR
            if task.errors:
                upload.logs = task.errors
            upload.save(update_fields=['status', 'logs'])
        except EntityUploadStatus.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'dataset_view_exporter':
        if len(task_param) == 0:
            return
        request_id = task_param[0]
        # update status_text to ABORTED
        request = ExportRequest.objects.filter(id=request_id).first()
        if request is None:
            return
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.status = ERROR
        if task.errors:
            request.errors = task.errors
        request.save(update_fields=['status_text', 'status', 'errors'])


def handle_task_interrupted(task: BackgroundTask):
    from dashboard.models import (
        EntityUploadStatus, STARTED, REVIEWING,
        LayerUploadSession, PROCESSING_APPROVAL,
        BatchReview, PENDING, PROCESSING
    )
    from dashboard.tasks.export import (
        generate_view_resource_vector_tiles_task,
        view_vector_tiles_task
    )
    from dashboard.tasks.upload import (
        validate_ready_uploads,
        run_comparison_boundary,
        layer_upload_preprocessing
    )
    from dashboard.tasks.review import (
        review_approval,
        process_batch_review,
        revert_process_batch_review_approval
    )
    task_name = task.name
    parameters = task.parameters
    task_param = make_tuple(parameters)
    logger.info(f'Found interrupted task {task_name} '
                f'with parameters {parameters}')
    if task_name == 'generate_view_resource_vector_tiles_task':
        # when vt is interrupted, we can safely resume the task
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter generate_view_resource_vector_tiles_task')
        try:
            view_resource_id = task_param[0]
            resource = DatasetViewResource.objects.filter(
                id=view_resource_id).first()
            if resource is None:
                return
            overwrite = False
            log_object_id = (
                int(task_param[2]) if len(task_param) > 2 and
                task_param[2] is not None else None
            )
            resource.status = (
                DatasetView.DatasetViewStatus.PENDING
            )
            resource.vector_tile_sync_status = (
                DatasetViewResource.SyncStatus.SYNCING
            )
            resource.tiling_current_task = None
            resource.save()
            task_celery = (
                generate_view_resource_vector_tiles_task.apply_async(
                    (
                        view_resource_id,
                        overwrite,
                        log_object_id
                    ),
                    queue='tegola'
                )
            )
            resource.vector_tiles_task_id = task_celery.id
            resource.save(update_fields=['vector_tiles_task_id'])
        except DatasetViewResource.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'view_vector_tiles_task':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter view_vector_tiles_task')
        try:
            view_id = task_param[0]
            overwrite = task_param[1] if len(task_param) > 2 else True
            view = DatasetView.objects.filter(id=view_id).first()
            if view is None:
                return
            view.simplification_current_task = None
            view.save(update_fields=['simplification_current_task'])
            task_celery = view_vector_tiles_task.delay(
                view.id, overwrite)
            view.task_id = task_celery.id
            view.save(update_fields=['task_id'])
        except DatasetView.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'validate_ready_uploads':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter validate_ready_uploads')
        try:
            upload_id = task_param[0]
            log_object_id = (
                int(task_param[1]) if len(task_param) > 1 and
                task_param[1] is not None else None
            )
            upload = EntityUploadStatus.objects.filter(id=upload_id).first()
            if upload is None:
                return
            # validate if upload is not in final state
            if upload.status in [STARTED, PROCESSING]:
                # reset the status back to STARTED
                upload.status = STARTED
                upload.save(update_fields=['status'])
                task_celery = validate_ready_uploads.apply_async(
                    (
                        upload.id,
                        log_object_id
                    ),
                    queue='validation'
                )
                upload.task_id = task_celery.id
                upload.save(update_fields=['task_id'])
        except EntityUploadStatus.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'run_comparison_boundary':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter run_comparison_boundary')
        try:
            upload_id = task_param[0]
            upload = EntityUploadStatus.objects.filter(id=upload_id).first()
            if upload is None:
                return
            upload_session: LayerUploadSession = upload.upload_session
            dataset: Dataset = upload_session.dataset
            # if boundary match ready, then skip
            if not upload.comparison_data_ready:
                # call ready_to_review func to reset state
                uploads = EntityUploadStatus.objects.filter(
                    id=upload_id
                )
                ready_to_review_func = module_function(
                    dataset.module.code_name,
                    'prepare_review',
                    'ready_to_review')
                ready_to_review_func(uploads)
                # update upload session status to REVIEWING
                upload_session.status = REVIEWING
                upload_session.save(update_fields=['status'])
                upload.refresh_from_db()
                task_celery = run_comparison_boundary.apply_async(
                    (upload.id,),
                    queue='validation'
                )
                upload.task_id = task_celery.id
                upload.save(update_fields=['task_id'])
        except EntityUploadStatus.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'review_approval':
        if len(task_param) < 3:
            raise ValueError(
                'Invalid parameter review_approval')
        try:
            upload_id = task_param[0]
            upload = EntityUploadStatus.objects.filter(id=upload_id).first()
            if upload is None:
                return
            upload_session: LayerUploadSession = upload.upload_session
            dataset: Dataset = upload_session.dataset
            user_id = task_param[1]
            upload_log_id = task_param[2]
            revert_approval_func = module_function(
                dataset.module.code_name,
                'review',
                'revert_approve_revision')
            revert_approval_func(upload)
            celery_task = review_approval.delay(
                upload_id,
                user_id,
                upload_log_id
            )
            upload.task_id = celery_task.id
            upload.status = PROCESSING_APPROVAL
            upload.save(update_fields=['task_id', 'status'])
        except EntityUploadStatus.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'process_batch_review':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter process_batch_review')
        try:
            batch_id = task_param[0]
            batch_review = BatchReview.objects.filter(id=batch_id).first()
            if batch_review is None:
                return
            batch_review.status = PENDING
            if batch_review.is_approve:
                celery_task = revert_process_batch_review_approval.delay(
                    batch_id)
                batch_review.task_id = celery_task.task_id
            else:
                celery_task = process_batch_review.delay(batch_id)
                batch_review.task_id = celery_task.task_id
            batch_review.save(update_fields=['status', 'task_id'])
        except BatchReview.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'layer_upload_preprocessing':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter layer_upload_preprocessing')
        try:
            upload_session_id = task_param[0]
            log_object_id = (
                int(task_param[1]) if len(task_param) > 1 and
                task_param[1] is not None else None
            )
            upload_session = LayerUploadSession.objects.filter(
                id=upload_session_id).first()
            if upload_session is None:
                return
            celery_task = layer_upload_preprocessing.delay(
                upload_session.id,
                log_object_id
            )
            upload_session.task_id = task.id
            upload_session.save(update_fields=['task_id'])
        except LayerUploadSession.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'dataset_view_exporter':
        if len(task_param) == 0:
            return
        request_id = task_param[0]
        # update status_text to ABORTED
        request = ExportRequest.objects.filter(id=request_id).first()
        if request is None:
            return
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.status = ERROR
        if task.errors:
            request.errors = task.errors
        else:
            request.errors = 'Job is interrupted!'
        request.save(update_fields=['status_text', 'status', 'errors'])


@shared_task(name="remove_old_background_tasks")
def remove_old_background_tasks():
    datetime_filter = timezone.now() - timedelta(days=REMOVE_AFTER_DAYS)
    tasks = BackgroundTask.objects.filter(
        last_update__lte=datetime_filter
    )
    logger.info(f'Removing old background task with count {tasks.count()}')
    tasks.delete()
