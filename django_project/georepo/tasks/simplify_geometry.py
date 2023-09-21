import logging
from celery import shared_task
from georepo.models import Dataset, DatasetView
from georepo.utils.mapshaper import (
    simplify_for_dataset,
    simplify_for_dataset_view
)

logger = logging.getLogger(__name__)


@shared_task(name="simplify_geometry_in_dataset")
def simplify_geometry_in_dataset(dataset_id):
    """Manual trigger of simplification in dataset."""
    dataset = Dataset.objects.get(id=dataset_id)
    logger.info(f'Running simplify geometry for dataset {dataset}')
    simplify_for_dataset(dataset)
    logger.info(
        f'Simplify geometry for dataset {dataset} is finished.')


@shared_task(name="simplify_geometry_in_view")
def simplify_geometry_in_view(dataset_view_id):
    """
    Manual trigger of simplification in view with custom tiling config.
    """
    view = DatasetView.objects.get(id=dataset_view_id)
    logger.info(f'Running simplify geometry for view {view}')
    simplify_for_dataset_view(view)
    logger.info(
        f'Simplify geometry for view {view} is finished.')
