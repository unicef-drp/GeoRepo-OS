from celery import shared_task, states
import logging
from django.utils import timezone
from ast import literal_eval as make_tuple
from georepo.models import (
    BackgroundTask,
    DatasetViewResource,
    DatasetView
)
from georepo.utils.celery_helper import get_task_status, TASK_NOT_FOUND


logger = logging.getLogger(__name__)


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
        # check using flower API
        status = get_task_status(task.task_id)
        if status == states.FAILURE:
            handle_task_failure(task)
        elif status == TASK_NOT_FOUND:
            handle_task_interrupted(task)


def on_task_invalidated(task: BackgroundTask):
    task.status = BackgroundTask.BackgroundTaskStatus.INVALIDATED
    task.last_update = timezone.now()
    task.save(update_fields=['status', 'last_update'])


def handle_task_failure(task: BackgroundTask):
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
            resource = DatasetViewResource.objects.get(
                id=view_resource_id)
            export_data = (
                task_param[1] if len(task_param) > 1 else True
            )
            resource.status = DatasetView.DatasetViewStatus.ERROR
            resource.vector_tile_sync_status = (
                DatasetViewResource.SyncStatus.ERROR
            )
            if export_data:
                fields = [
                    'geojson_sync_status',
                    'shapefile_sync_status',
                    'kml_sync_status',
                    'topojson_sync_status'
                ]
                for field in fields:
                    setattr(resource, field,
                            DatasetViewResource.SyncStatus.ERROR)
            resource.save()
        except DatasetViewResource.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'view_vector_tiles_task':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter view_vector_tiles_task')
        try:
            view_id = task_param[0]
            view = DatasetView.objects.get(id=view_id)
            view.status = DatasetView.DatasetViewStatus.ERROR
            view.simplification_progress = 'Simplification error'
            view.save()
        except DatasetView.DoesNotExist as ex:
            logger.error(ex)
    on_task_invalidated(task)


def handle_task_interrupted(task: BackgroundTask):
    from dashboard.tasks.export import (
        generate_view_resource_vector_tiles_task,
        view_vector_tiles_task
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
            resource = DatasetViewResource.objects.get(
                id=view_resource_id)
            export_data = (
                task_param[1] if len(task_param) > 1 else True
            )
            export_vector_tile = (
                task_param[2] if len(task_param) > 2 else True
            )
            overwrite = False
            log_object_id = (
                int(task_param[4]) if len(task_param) > 4 else None
            )
            resource.status = (
                DatasetView.DatasetViewStatus.PENDING
            )
            resource.vector_tile_sync_status = (
                DatasetViewResource.SyncStatus.SYNCING
            )
            if export_data:
                fields = [
                    'geojson_sync_status',
                    'shapefile_sync_status',
                    'kml_sync_status',
                    'topojson_sync_status'
                ]
                for field in fields:
                    setattr(resource, field,
                            DatasetViewResource.SyncStatus.SYNCING)
            task_celery = (
                generate_view_resource_vector_tiles_task.apply_async(
                    (
                        view_resource_id,
                        export_data,
                        export_vector_tile,
                        overwrite,
                        log_object_id
                    ),
                    queue='tegola'
                )
            )
            resource.vector_tiles_task_id = task_celery.id
            resource.save()
        except DatasetViewResource.DoesNotExist as ex:
            logger.error(ex)
    elif task_name == 'view_vector_tiles_task':
        if len(task_param) == 0:
            raise ValueError(
                'Invalid parameter view_vector_tiles_task')
        try:
            view_id = task_param[0]
            export_data = task_param[1] if len(task_param) > 1 else True
            export_vector_tile = (
                task_param[2] if len(task_param) > 2 else True
            )
            overwrite = task_param[3] if len(task_param) > 3 else True
            view = DatasetView.objects.get(id=view_id)
            task_celery = view_vector_tiles_task.delay(
                view.id, export_data, export_vector_tile, overwrite)
            view.task_id = task_celery.id
            view.save(update_fields=['task_id'])
            view.save()
        except DatasetView.DoesNotExist as ex:
            logger.error(ex)
    on_task_invalidated(task)
