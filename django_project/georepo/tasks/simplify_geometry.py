import logging
from celery import shared_task
from georepo.utils.simplification import (
    process_simplification,
    process_simplification_for_view
)

logger = logging.getLogger(__name__)


@shared_task(name="simplify_geometry_in_dataset")
def simplify_geometry_in_dataset(dataset_id):
    logger.info(f'Running simplify geometry for dataset {dataset_id}')
    last_entity_id, total_count = process_simplification(dataset_id, limit=-1)
    logger.info(
        f'Simplify geometry for dataset {dataset_id} is finished: '
        f'{last_entity_id} - {total_count}')


@shared_task(name="simplify_geometry_in_view")
def simplify_geometry_in_view(dataset_view_id):
    logger.info(f'Running simplify geometry for view {dataset_view_id}')
    last_entity_id, total_count = process_simplification_for_view(
        dataset_view_id,
        limit=-1
    )
    logger.info(
        f'Simplify geometry for view {dataset_view_id} is finished: '
        f'{last_entity_id} - {total_count}')
