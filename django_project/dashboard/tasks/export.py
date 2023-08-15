from celery import shared_task
from celery.utils.log import get_task_logger

from georepo.utils import generate_view_vector_tiles

logger = get_task_logger(__name__)


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
            generate_view_geojson(view, view_resource)
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
        generate_view_geojson(view)
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
    except DatasetView.DoesNotExist:
        logger.error(f'DatasetView {view_id} does not exist')


@shared_task(name="generate_dataset_export_data")
def generate_dataset_export_data(dataset_id: str):
    from georepo.models.dataset import Dataset
    from georepo.utils.geojson import generate_geojson
    from georepo.utils.shapefile import generate_shapefile
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        logger.info('Extracting geojson from dataset...')
        generate_geojson(dataset)
        logger.info('Extracting shapefile from dataset...')
        generate_shapefile(dataset)
        logger.info('Extract dataset data done')
    except Dataset.DoesNotExist:
        logger.error(f'Dataset {dataset_id} does not exist')
