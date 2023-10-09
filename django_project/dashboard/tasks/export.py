import time
import os
from celery import shared_task
import logging
import shutil
from django.conf import settings

from georepo.utils import (
    generate_view_vector_tiles,
    remove_vector_tiles_dir,
    generate_view_resource_bbox,
    DirectoryClient
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


def clean_resource_export_data_directory(resource_id):
    export_data_dict = {
        'geojson': settings.GEOJSON_FOLDER_OUTPUT,
        'shapefile': settings.SHAPEFILE_FOLDER_OUTPUT,
        'kml': settings.KML_FOLDER_OUTPUT,
        'topojson': settings.TOPOJSON_FOLDER_OUTPUT
    }
    for output, export_dir in export_data_dict.items():
        if settings.USE_AZURE:
            output_dir = (
                f'media/export_data/{output}/'
                f'{str(resource_id)}'
            )
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            client.rmdir(output_dir)
        else:
            export_data = os.path.join(
                export_dir,
                resource_id
            )
            if os.path.exists(export_data):
                shutil.rmtree(export_data)
        temp_export_data = os.path.join(
            export_dir,
            f'temp_{resource_id}'
        )
        if os.path.exists(temp_export_data):
            shutil.rmtree(temp_export_data)


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
def view_vector_tiles_task(view_id: str, export_data: bool = True,
                           export_vector_tile: bool = True,
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
            if export_data:
                view_resource.geojson_progress = 0
                view_resource.shapefile_progress = 0
                view_resource.kml_progress = 0
                view_resource.topojson_progress = 0
                view_resource.geojson_sync_status = (
                    DatasetView.SyncStatus.SYNCING
                )
                view_resource.shapefile_sync_status = (
                    DatasetView.SyncStatus.SYNCING
                )
                view_resource.kml_sync_status = DatasetView.SyncStatus.SYNCING
                view_resource.topojson_sync_status = (
                    DatasetView.SyncStatus.SYNCING
                )
        else:
            view_resource.status = DatasetView.DatasetViewStatus.EMPTY
            view_resource.vector_tile_sync_status = (
                DatasetView.SyncStatus.SYNCED
            )
            view_resource.geojson_progress = 0
            view_resource.shapefile_progress = 0
            view_resource.kml_progress = 0
            view_resource.topojson_progress = 0
            view_resource.geojson_sync_status = DatasetView.SyncStatus.SYNCED
            view_resource.shapefile_sync_status = (
                DatasetView.SyncStatus.SYNCED
            )
            view_resource.kml_sync_status = DatasetView.SyncStatus.SYNCED
            view_resource.topojson_sync_status = DatasetView.SyncStatus.SYNCED
            remove_view_resource_data.delay(view_resource.resource_id)
        view_resource.save(update_fields=[
            'entity_count', 'status', 'vector_tile_sync_status',
            'vector_tiles_progress', 'geojson_progress',
            'shapefile_progress', 'kml_progress', 'topojson_progress',
            'shapefile_sync_status', 'kml_sync_status',
            'topojson_sync_status', 'geojson_sync_status'
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
                    export_data,
                    export_vector_tile,
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
                                             export_data: bool = True,
                                             export_vector_tile: bool = True,
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
    from georepo.utils.geojson import generate_view_geojson
    from georepo.utils.shapefile import generate_view_shapefile
    from georepo.utils.kml import generate_view_kml
    from georepo.utils.topojson import generate_view_topojson

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

        if export_vector_tile:
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
        if export_data:
            view = view_resource.dataset_view
            logger.info(
                f'Extracting geojson from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            geojson_exporter = generate_view_geojson(
                view,
                view_resource,
                **{'log_object': view_resource_log}
            )
            logger.info(
                f'Extracting shapefile from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_shapefile(
                view,
                view_resource,
                **{'log_object': view_resource_log}
            )
            logger.info(
                f'Extracting kml from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_kml(
                view,
                view_resource,
                **{'log_object': view_resource_log}
            )
            logger.info(
                f'Extracting topojson from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_topojson(
                view,
                view_resource,
                **{'log_object': view_resource_log}
            )
            logger.info('Extract view data done')
            if settings.USE_AZURE:
                logger.info('Removing temporary geojson files...')
                # cleanup geojson files if using Azure
                geojson_exporter.do_remove_temp_dirs()
                logger.info('Removing temporary geojson files done')
        end = time.time()
        view_resource_log.add_log(
                'generate_view_resource_vector_tiles_task',
                end - start
        )
    except DatasetViewResource.DoesNotExist:
        logger.error(f'DatasetViewResource {view_resource_id} does not exist')


@shared_task(name="generate_view_export_data")
def generate_view_export_data(view_resource_id: str):
    from georepo.models.dataset_view import DatasetView, DatasetViewResource
    from georepo.utils.geojson import generate_view_geojson
    from georepo.utils.shapefile import generate_view_shapefile
    from georepo.utils.kml import generate_view_kml
    from georepo.utils.topojson import generate_view_topojson
    try:
        resource = DatasetViewResource.objects.get(id=view_resource_id)
        view = resource.dataset_view
        entity_count = get_entities_count_in_view(
            view,
            resource.privacy_level
        )
        if entity_count == 0:
            resource.entity_count = entity_count
            resource.status = DatasetView.DatasetViewStatus.EMPTY
            resource.vector_tile_sync_status = (
                DatasetView.SyncStatus.SYNCED
            )
            resource.geojson_progress = 0
            resource.shapefile_progress = 0
            resource.kml_progress = 0
            resource.topojson_progress = 0
            resource.geojson_sync_status = DatasetView.SyncStatus.SYNCED
            resource.shapefile_sync_status = (
                DatasetView.SyncStatus.SYNCED
            )
            resource.kml_sync_status = DatasetView.SyncStatus.SYNCED
            resource.topojson_sync_status = DatasetView.SyncStatus.SYNCED
            resource.save(update_fields=[
                'entity_count', 'status', 'vector_tile_sync_status',
                'vector_tiles_progress', 'geojson_progress',
                'shapefile_progress', 'kml_progress', 'topojson_progress',
                'shapefile_sync_status', 'kml_sync_status',
                'topojson_sync_status', 'geojson_sync_status'
            ])
            clean_resource_export_data_directory(resource.resource_id)
            return
        logger.info(
            f'Extracting geojson from view {view.name} - '
            f'{resource.privacy_level}...'
        )
        geojson_exporter = generate_view_geojson(view, resource)
        logger.info(
            f'Extracting shapefile from view {view.name} - '
            f'{resource.privacy_level}...'
        )
        generate_view_shapefile(view, resource)
        logger.info(
            f'Extracting kml from view {view.name} - '
            f'{resource.privacy_level}...'
        )
        generate_view_kml(view, resource)
        logger.info(
            f'Extracting topojson from view {view.name} - '
            f'{resource.privacy_level}...'
        )
        generate_view_topojson(view, resource)

        logger.info('Extract view data done')
        if settings.USE_AZURE:
            logger.info('Removing temporary geojson files...')
            # cleanup geojson files if using Azure
            geojson_exporter.do_remove_temp_dirs()
            logger.info('Removing temporary geojson files done')
    except DatasetViewResource.DoesNotExist:
        logger.error(f'DatasetViewResource {view_resource_id} does not exist')


@shared_task(name="remove_view_resource_data")
def remove_view_resource_data(resource_id: str):
    clean_resource_vector_tiles_directory(resource_id)
    clean_resource_export_data_directory(resource_id)
