from celery import shared_task
from dashboard.models.batch_edit import BatchEntityEdit
from dashboard.tools.entity_edit import get_entity_edit_importer


@shared_task(name="process_batch_entity_edit")
def process_batch_entity_edit(batch_entity_edit_id, preview):
    batch_edit = BatchEntityEdit.objects.get(id=batch_entity_edit_id)
    importer = get_entity_edit_importer(batch_edit, preview)
    importer.start()
