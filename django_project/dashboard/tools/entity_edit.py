import logging
import csv
import tempfile
import re
from django.utils import timezone
from django.db.models import Max
from django.db.models.fields.files import FieldFile


from georepo.models.id_type import IdType
from georepo.models.language import Language
from georepo.models.base_task_request import PROCESSING, DONE, ERROR
from georepo.models.entity import (
    GeographicalEntity,
    EntityId,
    EntityName
)
from dashboard.models.batch_edit import BatchEntityEdit
from georepo.utils.unique_code import parse_unique_code


logger = logging.getLogger(__name__)


def try_delete_uploaded_file(file: FieldFile):
    try:
        file.delete(save=False)
    except Exception:
        logger.error('Failed to delete file!')


class BatchEntityEditBaseImporter(object):
    request = BatchEntityEdit.objects.none()
    headers = []
    ucode_index = -1
    # store name/id fields with its index
    name_fields = {}
    id_fields = {}
    # validation of missing columns
    missing_columns = []
    # metadata
    id_types = IdType.objects.all()
    languages = Language.objects.all()

    def __init__(self, request: BatchEntityEdit) -> None:
        self.request = request

    def process_started(self):
        # reset state, clear exiting output
        self.headers = []
        self.ucode_index = -1
        self.name_fields = {}
        self.id_fields = {}
        self.missing_columns = []
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

    def read_headers(self):
        """Read column headers."""
        pass

    def process_headers(self):
        """Read headers."""
        # find index of ucode_field in headers
        for idx, header in enumerate(self.headers):
            if header == self.request.ucode_field:
                self.ucode_index = idx
            check_id = (
                [id_field for id_field in self.request.id_fields if
                 id_field['field'] == header]
            )
            if len(check_id) > 0:
                self.id_fields[idx] = check_id[0]
            check_name = (
                [name_field for name_field in self.request.name_fields if
                 name_field['field'] == header]
            )
            if len(check_name) > 0:
                self.name_fields[idx] = check_name[0]

    def validate_headers(self):
        """Validate mandatory columns."""
        self.missing_columns = []
        if self.ucode_index == -1:
            self.missing_columns.append(self.request.ucode_field)
        for id_field in self.request.id_fields:
            field_name = id_field['field']
            check_fields = (
                [field for field in self.id_fields.values() if
                 field['field'] == field_name]
            )
            if len(check_fields) == 0:
                self.missing_columns.append(field_name)
        for name_field in self.request.name_fields:
            field_name = name_field['field']
            check_fields = (
                [field for field in self.name_fields.values() if
                 field['field'] == field_name]
            )
            if len(check_fields) == 0:
                self.missing_columns.append(field_name)
        return len(self.missing_columns) == 0

    def process_row(self, row):
        """
        Process individual row.

        :param row: list of cell values
        :return: Tuple of is_success, error_message, updated_rows
        """
        updated_rows = []
        # parse ucode
        ucode = row[self.ucode_index]
        try:
            unique_code, version_number = parse_unique_code(ucode)
        except ValueError as ex:
            return False, str(ex), updated_rows
        # find entity
        entity = GeographicalEntity.objects.select_related(
            'ancestor'
        ).defer(
            'geometry', 'ancestor__geometry'
        ).filter(
            dataset=self.request.dataset,
            unique_code=unique_code,
            unique_code_version=version_number,
            is_approved=True
        )
        if not entity.exists():
            return False, f'Entity {ucode} does not exist', updated_rows
        entity = entity.first()
        # fetch entity metadata: existing names, existing ids
        entity_ids = list(EntityId.objects.select_related('code').filter(
            geographical_entity=entity
        ).all())
        entity_names = list(EntityName.objects.filter(
            geographical_entity=entity
        ).all())
        # process new id_fields
        id_errors = []
        id_warns = []
        new_ids = []
        for id_field_idx, id_field in self.id_fields.items():
            field_name = id_field['field']
            id_value = self.row_value(row, id_field_idx)
            # validate non-empty value
            if id_value == '':
                id_errors.append(f'Invalid value of {field_name}')
                continue
            # get the id_type
            id_type_in = id_field['idType']
            id_type = (
                [id for id in self.id_types if id.id == id_type_in['id']]
            )
            if len(id_type) == 0:
                continue
            id_type = id_type[0]
            # validate non-duplicate id type
            is_existing_id = (
                [id for id in entity_ids if id.code.id == id_type.id]
            )
            if len(is_existing_id) > 0:
                id_warns.append(f'Existing ID {field_name}')
                continue
            # validate non-duplicate id value
            is_existing_value = (
                [id for id in entity_ids if id.value == id_value]
            )
            if len(is_existing_value) > 0:
                id_warns.append(f'Existing ID value {id_value}')
                continue
            # add to new_ids
            new_ids.append(EntityId(
                geographical_entity=entity,
                code=id_type,
                value=id_value
            ))

        # get max value of idx in EntityName
        name_idx_start = 0
        max_idx_res = EntityName.objects.filter(
            geographical_entity=entity
        ).aggregate(Max('idx'))
        if max_idx_res:
            name_idx_start = max_idx_res['idx__max'] + 1
        # process new name_fields
        name_errors = []
        name_warns = []
        new_names = []
        for name_field_idx, name_field in self.name_fields.items():
            field_name = name_field['field']
            name_value = self.row_value(row, name_field_idx)
            # validate non-empty value
            if name_value == '':
                name_errors.append(f'Invalid value of {field_name}')
                continue
            # get the language
            lang_in = name_field['selectedLanguage']
            language = [lang for lang in self.languages if lang.id == lang_in]
            if len(language) == 0:
                continue
            language = language[0]
            # find duplicate name by language and value
            is_existing_name = (
                [name for name in entity_names if
                 name.name == name_value and name.language.id == lang_in]
            )
            if len(is_existing_name) > 0:
                name_warns.append(f'Existing name {name_value}')
                continue
            # add to new_names
            new_names.append(EntityName(
                name=name_value,
                geographical_entity=entity,
                language=language,
                label=name_field['label'],
                idx=name_idx_start
            ))
            name_idx_start += 1

        # if there is no errors, then save the new ids and names
        if len(id_errors) > 0 or len(name_errors) > 0:
            errors = [', '.join(id_errors), ', '.join(name_errors)]
            return False, ', '.join(errors), updated_rows
        # TODO: return warnings/updated_rows
        if new_ids:
            EntityId.objects.bulk_create(new_ids)
        if new_names:
            EntityName.objects.bulk_create(new_names)
        return True, None, updated_rows

    def row_value(self, row, index):
        """
        Get row value by index
        :param row: row data
        :param index: index
        :return: row value
        """
        row_value = ''
        try:
            row_value = row[index]
            row_value = row_value.replace('\xa0', ' ')
            row_value = row_value.replace('\xc2', '')
            row_value = row_value.replace('\\xa0', '')
            row_value = row_value.strip()
            row_value = re.sub(' +', ' ', row_value)
        except KeyError:
            pass
        return row_value
