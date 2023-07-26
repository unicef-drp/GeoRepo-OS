import logging
from django.db.models.expressions import RawSQL
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.models.dataset_view import DatasetView

logger = logging.getLogger(__name__)


def process_simplification(dataset_id, start_id=None, limit=1000):
    """
    Process simplification of geographical entities
    Return last processed id and total count processed
    """
    dataset = Dataset.objects.get(id=dataset_id)
    entities = GeographicalEntity.objects.filter(
        dataset_id=dataset_id
    ).order_by('id')
    if start_id:
        entities = entities.filter(id__gt=start_id)
    if limit != -1:
        entities = entities[:limit]
    processed = 0
    total_count = entities.count()
    entities = entities.iterator(chunk_size=1)
    last_entity_id = None
    dataset.simplification_progress = (
        f'Entity simplification ({processed}/{total_count})'
    )
    dataset.save(update_fields=['simplification_progress'])
    logger.info(dataset.simplification_progress)
    for entity in entities:
        entity.do_simplification()
        last_entity_id = entity.id
        processed += 1
        if processed % 500 == 0:
            logger.info(f'Entity simplification ({processed}/{total_count})')
        if processed % 100 == 0:
            dataset.simplification_progress = (
                f'Entity simplification finished ({processed}/{total_count})'
            )
            dataset.save(update_fields=['simplification_progress'])
    dataset.simplification_progress = (
        f'Entity simplification finished ({processed}/{total_count})'
    )
    dataset.save(update_fields=['simplification_progress'])
    logger.info(dataset.simplification_progress)
    logger.info(f'last id {last_entity_id}')
    return last_entity_id, total_count


def process_simplification_for_view(dataset_view_id,
                                    start_id=None, limit=1000):
    """
    Process simplification of geographical entities
    Return last processed id and total count processed
    """
    dataset_view = DatasetView.objects.get(id=dataset_view_id)
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(dataset_view.uuid))
    entities = GeographicalEntity.objects.filter(
        dataset=dataset_view.dataset
    ).filter(
        id__in=RawSQL(raw_sql, [])
    ).order_by('id')
    if start_id:
        entities = entities.filter(id__gt=start_id)
    if limit != -1:
        entities = entities[:limit]
    processed = 0
    total_count = entities.count()
    entities = entities.iterator(chunk_size=1)
    last_entity_id = None
    dataset_view.simplification_progress = (
        f'Entity simplification ({processed}/{total_count})'
    )
    dataset_view.save(update_fields=['simplification_progress'])
    logger.info(dataset_view.simplification_progress)
    for entity in entities:
        entity.do_simplification()
        last_entity_id = entity.id
        processed += 1
        if processed % 500 == 0:
            logger.info(f'Entity simplification ({processed}/{total_count})')
        if processed % 100 == 0:
            dataset_view.simplification_progress = (
                f'Entity simplification finished ({processed}/{total_count})'
            )
            dataset_view.save(update_fields=['simplification_progress'])
    dataset_view.simplification_progress = (
        f'Entity simplification finished ({processed}/{total_count})'
    )
    dataset_view.save(update_fields=['simplification_progress'])
    logger.info(dataset_view.simplification_progress)
    logger.info(f'last id {last_entity_id}')
    return last_entity_id, total_count
