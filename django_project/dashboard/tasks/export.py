import time
import os
from celery import shared_task
from celery.result import AsyncResult
from core.celery import app
import logging
import shutil
from django.conf import settings

from georepo.utils import (
    generate_view_vector_tiles,
    remove_vector_tiles_dir,
    generate_view_resource_bbox
)

logger = logging.getLogger(__name__)


@shared_task(name="view_vector_tiles_task")
def view_vector_tiles_task(view_id: str, export_data: bool = True,
                           export_vector_tile: bool = True,
                           overwrite: bool = True):
    """Entrypoint of view vector tile generation."""
    from georepo.models.dataset_view import (
        DatasetView, DatasetViewResource
    )
    from georepo.utils.mapshaper import (
        simplify_for_dataset,
        simplify_for_dataset_view
    )
    from georepo.utils.dataset_view import (
        get_entities_count_in_view
    )
    view = DatasetView.objects.get(id=view_id)
    # NOTE: need to handle on how to scale the simplification
    # before vector tile because right now tile queue is only set
    # to 1 concurrency.
    if not view.dataset.is_simplified:
        # simplification for dataset if tiling config is updated
        is_simplification_success = simplify_for_dataset(
            view.dataset
        )
        if not is_simplification_success:
            raise RuntimeError('Dataset Simplification Failed!')
    # trigger simplificatin for view
    is_simplification_success = simplify_for_dataset_view(
        view
    )
    if not is_simplification_success:
        raise RuntimeError('View Simplification Failed!')

    view_resources = DatasetViewResource.objects.filter(
        dataset_view=view
    )
    for view_resource in view_resources:
        if view_resource.vector_tiles_task_id:
            res = AsyncResult(view_resource.vector_tiles_task_id)
            if not res.ready():
                # find if there is running task and stop it
                app.control.revoke(
                    view_resource.vector_tiles_task_id,
                    terminate=True,
                    signal='SIGKILL'
                )
        entity_count = get_entities_count_in_view(
            view_resource.dataset_view,
            view_resource.privacy_level
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
        view_resource.save()
        if entity_count > 0:
            task = generate_view_resource_vector_tiles_task.apply_async(
                (view_resource.id, export_data,
                 export_vector_tile, overwrite),
                queue='tegola'
            )
            view_resource.vector_tiles_task_id = task.id
            view_resource.save(update_fields=['vector_tiles_task_id'])


@shared_task(name="generate_view_resource_vector_tiles_task")
def generate_view_resource_vector_tiles_task(view_resource_id: str,
                                             export_data: bool = True,
                                             export_vector_tile: bool = True,
                                             overwrite: bool = True):
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
        try:
            view_resource_log, _ = \
                DatasetViewResourceLog.objects.get_or_create(
                    dataset_view_resource=view_resource,
                    task_id=view_resource.vector_tiles_task_id
                )
        except DatasetViewResourceLog.DoesNotExist:
            view_resource_log = DatasetViewResourceLog.objects.create(
                dataset_view_resource=view_resource
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
def generate_view_export_data(view_id: str):
    from georepo.models.dataset_view import DatasetView
    from georepo.utils.geojson import generate_view_geojson
    from georepo.utils.shapefile import generate_view_shapefile
    from georepo.utils.kml import generate_view_kml
    from georepo.utils.topojson import generate_view_topojson

    try:
        view = DatasetView.objects.get(id=view_id)
        logger.info(f'Extracting geojson from view {view.name}...')
        geojson_exporter = generate_view_geojson(view)
        logger.info(
            f'Extracting shapefile from view {view.name}...'
        )
        generate_view_shapefile(view)
        logger.info(
            f'Extracting kml from view {view.name}...'
        )
        generate_view_kml(view)
        logger.info(
            f'Extracting topojson from view {view.name}...'
        )
        generate_view_topojson(view)

        logger.info('Extract view data done')
        if settings.USE_AZURE:
            logger.info('Removing temporary geojson files...')
            # cleanup geojson files if using Azure
            geojson_exporter.do_remove_temp_dirs()
            logger.info('Removing temporary geojson files done')
    except DatasetView.DoesNotExist:
        logger.error(f'DatasetView {view_id} does not exist')


@shared_task(name="remove_view_resource_data")
def remove_view_resource_data(resource_id: str):
    # remove vector tiles dir
    remove_vector_tiles_dir(resource_id)
    remove_vector_tiles_dir(resource_id, True)
    export_data_list = [
        settings.GEOJSON_FOLDER_OUTPUT,
        settings.SHAPEFILE_FOLDER_OUTPUT,
        settings.KML_FOLDER_OUTPUT,
        settings.TOPOJSON_FOLDER_OUTPUT
    ]
    for export_dir in export_data_list:
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
