import os
from celery import shared_task
import logging
import shutil
from django.conf import settings

from georepo.utils import (
    generate_view_vector_tiles,
    remove_vector_tiles_dir
)

logger = logging.getLogger(__name__)


@shared_task(name="generate_view_vector_tiles")
def generate_view_vector_tiles_task(view_resource_id: str,
                                    export_data: bool = True,
                                    overwrite: bool = True):
    from georepo.models.dataset_view import DatasetViewResource
    from georepo.utils.geojson import generate_view_geojson
    from georepo.utils.shapefile import generate_view_shapefile
    from georepo.utils.kml import generate_view_kml
    from georepo.utils.topojson import generate_view_topojson

    try:
        view_resource = DatasetViewResource.objects.get(id=view_resource_id)
        logger.info(
            f'Generating vector tile from view_resource {view_resource.id} '
            f'- {view_resource.privacy_level} '
            f'- {view_resource.dataset_view.name}'
        )
        generate_view_vector_tiles(view_resource, overwrite=overwrite)
        if export_data:
            view = view_resource.dataset_view
            logger.info(
                f'Extracting geojson from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            geojson_exporter = generate_view_geojson(view, view_resource)
            logger.info(
                f'Extracting shapefile from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_shapefile(view, view_resource)
            logger.info(
                f'Extracting kml from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_kml(view, view_resource)
            logger.info(
                f'Extracting topojson from view {view.name} - '
                f'{view_resource.privacy_level}...'
            )
            generate_view_topojson(view, view_resource)
            logger.info('Extract view data done')
            if settings.USE_AZURE:
                logger.info('Removing temporary geojson files...')
                # cleanup geojson files if using Azure
                geojson_exporter.do_remove_temp_dirs()
                logger.info('Removing temporary geojson files done')
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
