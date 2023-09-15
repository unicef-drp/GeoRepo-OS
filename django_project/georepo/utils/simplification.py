import logging
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.utils.mapshaper import simplify_for_dataset

logger = logging.getLogger(__name__)


def process_simplification(dataset_id):
    """
    Process simplification of geographical entities
    """
    dataset = Dataset.objects.get(id=dataset_id)
    dataset.simplification_progress = (
        'Entity simplification starts'
    )
    dataset.save(update_fields=['simplification_progress'])
    logger.info(dataset.simplification_progress)
    simplify_for_dataset(dataset)
    dataset.simplification_progress = (
        f'Entity simplification finished for {dataset}'
    )
    dataset.save(update_fields=['simplification_progress'])
    logger.info(dataset.simplification_progress)


def process_simplification_for_view(dataset_view_id):
    """
    Process simplification of geographical entities from view
    """
    dataset_view = DatasetView.objects.get(id=dataset_view_id)
    dataset_view.simplification_progress = (
        f'Entity simplification for view {dataset_view}'
    )
    dataset_view.save(update_fields=['simplification_progress'])
    logger.info(dataset_view.simplification_progress)
    process_simplification(dataset_view.dataset.id)
    dataset_view.simplification_progress = (
        f'Entity simplification finished {dataset_view}'
    )
    dataset_view.save(update_fields=['simplification_progress'])
    logger.info(dataset_view.simplification_progress)
