import logging
import csv
import tempfile
from django.utils import timezone
from django.db.models.fields.files import FieldFile


from georepo.models.base_task_request import PROCESSING, DONE, ERROR
from georepo.models.entity import (
    GeographicalEntity,
    EntityId,
    EntityName
)
from dashboard.models.batch_edit import BatchEntityEdit


logger = logging.getLogger(__name__)


def try_delete_uploaded_file(file: FieldFile):
    try:
        file.delete(save=False)
    except Exception:
        logger.error('Failed to delete file!')


class BatchEntityEditImporter(object):
    request = BatchEntityEdit.objects.none()

    def __init__(self, request: BatchEntityEdit) -> None:
        self.request = request

    def process_started(self):
        # reset state, clear exiting output
        self.request.status = PROCESSING
        self.request.started_at = timezone.now()
        self.request.finished_at = None
        self.request.progress = 0
        self.request.errors = None
        if self.request.output_file:
            try_delete_uploaded_file(self.request.output_file)
            self.request.output_file = None
        self.request.error_notes = None
        self.request.error_count = None
        self.request.success_notes = None
        self.request.total_count = None
        self.request.save(update_fields=[
            'status', 'started_at', 'progress', 'errors',
            'finished_at', 'output_file', 'error_notes',
            'error_count', 'total_count', 'success_notes'
        ])

    def process_ended(self, is_success, errors = None):
        # set final state, clear temp resource
        self.request.status = DONE if is_success else ERROR
        if not is_success:
            self.request.errors = errors
        self.request.finished_at = timezone.now()
        self.request.save(update_fields=['status', 'finished_at', 'errors'])

    def on_update_progress(self, row, total_count):
        # save progress of task
        self.request.total_count = total_count
        self.request.progress = (
            (row / total_count) * 100 if total_count else 0
        )
        self.request.save(update_fields=['total_count', 'progress'])

    def start(self):
        pass

    def process_row(self, row):
        pass
