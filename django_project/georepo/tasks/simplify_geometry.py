import logging
from celery import shared_task
from georepo.models import (
    DatasetView,
    DatasetViewTilingConfig
)
from georepo.utils.simplification import (
    process_simplification,
    process_simplification_for_view
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view
)

logger = logging.getLogger(__name__)


@shared_task(name="simplify_geometry_in_dataset")
def simplify_geometry_in_dataset(dataset_id):
    logger.info(f'Running simplify geometry for dataset {dataset_id}')
    process_simplification(dataset_id)
    views = DatasetView.objects.filter(
        dataset_id=dataset_id
    )
    for view in views:
        # check for view in dataset that inherits tiling config
        tiling_config_exists = DatasetViewTilingConfig.objects.filter(
            dataset_view=view
        ).exists()
        if tiling_config_exists:
            continue
        logger.info(f'Triggering vector tile generation for view {view}')
        trigger_generate_vector_tile_for_view(view, export_data=False)
    logger.info(
        f'Simplify geometry for dataset {dataset_id} is finished.')


@shared_task(name="simplify_geometry_in_view")
def simplify_geometry_in_view(dataset_view_id):
    logger.info(f'Running simplify geometry for view {dataset_view_id}')
    view = DatasetView.objects.get(
        id=dataset_view_id
    )
    process_simplification_for_view(
        dataset_view_id
    )
    trigger_generate_vector_tile_for_view(view, export_data=False)
    logger.info(f'Triggering vector tile generation for view {view}')
    logger.info(
        f'Simplify geometry for view {dataset_view_id} is finished.')
