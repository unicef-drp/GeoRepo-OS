import logging
import traceback
from celery import shared_task
from georepo.models.base_task_request import ERROR
from dashboard.models.batch_edit import BatchEntityEdit
from dashboard.tools.entity_edit import get_entity_edit_importer


logger = logging.getLogger(__name__)


@shared_task(name="process_batch_entity_edit")
def process_batch_entity_edit(batch_entity_edit_id, preview):
    batch_edit = BatchEntityEdit.objects.get(id=batch_entity_edit_id)
    try:
        importer = get_entity_edit_importer(batch_edit, preview)
        importer.start()
    except Exception as ex:
        logger.error('Failed Process Batch Entity Edit!')
        logger.error(ex)
        logger.error(traceback.format_exc())
        batch_edit.status = ERROR
        batch_edit.errors = str(ex)
        batch_edit.task_id = None
        batch_edit.save(update_fields=['status', 'errors', 'task_id'])
