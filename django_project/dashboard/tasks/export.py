import time
from celery import shared_task
import logging

from georepo.utils import (
    generate_view_vector_tiles,
    remove_vector_tiles_dir,
    generate_view_resource_bbox
)
from georepo.models.dataset_view import DatasetViewResourceLog
from georepo.models.dataset_view_tile_config import DatasetViewTilingConfig
from georepo.utils.dataset_view import (
    get_entities_count_in_view
)
from georepo.utils.celery_helper import cancel_task

logger = logging.getLogger(__name__)


def clean_resource_vector_tiles_directory(resource_id):
    # remove vector tiles dir
    remove_vector_tiles_dir(resource_id)
    remove_vector_tiles_dir(resource_id, True)


@shared_task(name="view_simplification_task")
def view_simplification_task(view_id: str):
    """Entrypoint of view/dataset simplification task."""
    from georepo.models.dataset_view import (
        DatasetView, DatasetViewResource
    )
    from georepo.utils.mapshaper import (
        simplify_for_dataset,
        simplify_for_dataset_view
    )
    view = DatasetView.objects.get(id=view_id)
    if view.task_id:
        cancel_task(view.task_id)
    view_resources = DatasetViewResource.objects.filter(
        dataset_view=view
    )
    for view_resource in view_resources:
        if view_resource.vector_tiles_task_id:
            cancel_task(view_resource.vector_tiles_task_id)
    # cancel any ongoing task for vector tile generation or
    # simplification task
    obj_log, _ = DatasetViewResourceLog.objects.get_or_create(
        dataset_view=view
    )
    kwargs = {
        'log_object': obj_log
    }
    has_view_tile_configs = DatasetViewTilingConfig.objects.filter(
        dataset_view=view
    ).exists()
    # NOTE: need to handle on how to scale the simplification
    # before vector tile because right now tile queue is only set
    # to 1 concurrency.
    if not view.dataset.is_simplified and not has_view_tile_configs:
        # simplification for dataset if tiling config is updated
        is_simplification_success = simplify_for_dataset(
            view.dataset,
            **kwargs
        )
        if not is_simplification_success:
            raise RuntimeError('Dataset Simplification Failed!')
    else:
        # trigger simplification for view
        is_simplification_success = simplify_for_dataset_view(
            view,
            **kwargs
        )
        if not is_simplification_success:
            raise RuntimeError('View Simplification Failed!')


@shared_task(name="view_vector_tiles_task")
def view_vector_tiles_task(view_id: str,
                           overwrite: bool = True):
    """
    Entrypoint of view vector tile generation.

    Pre-requisites: Simplification process.
    """
    from georepo.models.dataset_view import (
        DatasetView, DatasetViewResource
    )
    from georepo.utils.vector_tile import (
        reset_pending_tile_cache_keys,
        set_pending_tile_cache_keys
    )
    view = DatasetView.objects.get(id=view_id)
    obj_log, _ = DatasetViewResourceLog.objects.get_or_create(
        dataset_view=view
    )
    kwargs = {
        'log_object': obj_log
    }
    view_resources = DatasetViewResource.objects.filter(
        dataset_view=view
    )
    for view_resource in view_resources:
        if view_resource.vector_tiles_task_id:
            cancel_task(view_resource.vector_tiles_task_id)
        entity_count = get_entities_count_in_view(
            view_resource.dataset_view,
            view_resource.privacy_level,
            **kwargs
        )
        view_resource.entity_count = entity_count
        view_resource.vector_tiles_progress = 0
        if entity_count > 0:
            view_resource.status = DatasetView.DatasetViewStatus.PENDING
            view_resource.vector_tile_sync_status = (
                DatasetView.SyncStatus.SYNCING
            )
        else:
            view_resource.status = DatasetView.DatasetViewStatus.EMPTY
            view_resource.vector_tile_sync_status = (
                DatasetView.SyncStatus.SYNCED
            )
            remove_view_resource_data.delay(view_resource.resource_id)
        view_resource.save(update_fields=[
            'entity_count', 'status', 'vector_tile_sync_status',
            'vector_tiles_progress'
        ])

    for view_resource in view_resources:
        reset_pending_tile_cache_keys(view_resource)
        if view_resource.entity_count > 0:
            # check if it's zero tile, if yes, then can enable live vt
            # when there is existing vector tile, live vt will be enabled
            # after zoom level 0 generation
            if view_resource.vector_tiles_size == 0:
                set_pending_tile_cache_keys(view_resource)
                # update the size to 1, so API can return vector tile URL
                view_resource.vector_tiles_size = 1
            task = generate_view_resource_vector_tiles_task.apply_async(
                (
                    view_resource.id,
                    overwrite,
                    obj_log.id
                ),
                queue='tegola'
            )
            view_resource.vector_tiles_task_id = task.id
            view_resource.save(update_fields=['vector_tiles_task_id',
                                              'vector_tiles_size'])
        else:
            # clear directory if previous tile exists
            if view_resource.vector_tiles_size > 0:
                remove_vector_tiles_dir(view_resource.resource_id)
            view_resource.vector_tiles_size = 0
            view_resource.vector_tiles_task_id = ''
            view_resource.save(update_fields=['vector_tiles_task_id',
                                              'vector_tiles_size'])


@shared_task(name="generate_view_resource_vector_tiles_task")
def generate_view_resource_vector_tiles_task(view_resource_id: str,
                                             overwrite: bool = True,
                                             log_object_id=None):
    """
    Trigger vector tile generation only for view resource.

    Needs to ensure that simplification already happening
    before this function is called.
    """
    from georepo.models.dataset_view import (
        DatasetViewResource, DatasetViewResourceLog
    )

    try:
        start = time.time()
        view_resource = DatasetViewResource.objects.get(id=view_resource_id)
        if log_object_id:
            view_resource_log = DatasetViewResourceLog.objects.get(
                id=log_object_id
            )
        else:
            view_resource_log, _ = (
                DatasetViewResourceLog.objects.get_or_create(
                    dataset_view=view_resource.dataset_view
                )
            )

        logger.info(
            f'Generating vector tile from '
            f'view_resource {view_resource.id} '
            f'- {view_resource.privacy_level} '
            f'- {view_resource.dataset_view.name}'
        )
        generate_view_resource_bbox(
            view_resource,
            **{'log_object': view_resource_log}
        )
        generate_view_vector_tiles(
            view_resource,
            overwrite=overwrite,
            **{'log_object': view_resource_log})
        end = time.time()
        view_resource_log.add_log(
                'generate_view_resource_vector_tiles_task',
                end - start
        )
    except DatasetViewResource.DoesNotExist:
        logger.error(f'DatasetViewResource {view_resource_id} does not exist')


@shared_task(name="remove_view_resource_data")
def remove_view_resource_data(resource_id: str):
    clean_resource_vector_tiles_directory(resource_id)
