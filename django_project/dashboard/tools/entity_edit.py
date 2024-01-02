import logging
import os
import csv
import re
import traceback
import openpyxl
from django.conf import settings
from django.core.exceptions import ValidationError
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
TEMP_OUTPUT_DIRECTORY = getattr(
    settings, 'FILE_UPLOAD_TEMP_DIR',
    '/home/web/media/tmp/batch_entity_edit')
TEMP_OUTPUT_DIRECTORY = (
    TEMP_OUTPUT_DIRECTORY if
    TEMP_OUTPUT_DIRECTORY is not None else
    '/home/web/media/tmp/batch_entity_edit'
)


def try_delete_uploaded_file(file: FieldFile):
    try:
        file.delete(save=False)
    except Exception:
        logger.error('Failed to delete file!')


class BatchEntityEditBaseImporter(object):
    request = BatchEntityEdit.objects.none()
    headers = []
    total_rows = 0
    ucode_index = -1
    # store name/id fields with its index
    name_fields = {}
    id_fields = {}
    # validation of missing columns
    missing_columns = []
    # metadata
    id_types = IdType.objects.all()
    languages = Language.objects.all()
    # outputs
    output_headers = []
    csv_output_file_path = None
    csv_output_file = None
    csv_output_writer = None

    def __init__(self, request: BatchEntityEdit) -> None:
        self.request = request

    def process_started(self):
        # reset state, clear exiting output
        self.headers = []
        self.total_rows = 0
        self.ucode_index = -1
        self.name_fields = {}
        self.id_fields = {}
        self.missing_columns = []
        self.output_headers = []
        self.request.status = PROCESSING
        self.request.started_at = timezone.now()
        self.request.finished_at = None
        self.request.progress = 0
        self.request.errors = None
        if self.request.output_file:
            try_delete_uploaded_file(self.request.output_file)
            self.request.output_file = None
        self.request.error_notes = None
        self.request.error_count = 0
        self.request.success_notes = None
        self.request.success_count = 0
        self.request.save(update_fields=[
            'status', 'started_at', 'progress', 'errors',
            'finished_at', 'output_file', 'error_notes',
            'error_count', 'success_notes',
            'success_count'
        ])

    def remove_csv_output_file(self):
        if self.csv_output_file_path:
            try:
                if os.path.exists(self.csv_output_file_path):
                    os.remove(self.csv_output_file_path)
            except Exception as ex:
                logger.warn('Failed to delete csv output file: ')
                logger.warn(ex)
                logger.warn(traceback.format_exc())

    def process_ended(self, is_success, errors = None):
        # set final state, clear temp resource
        self.request.status = DONE if is_success else ERROR
        if not is_success:
            self.request.errors = errors
        self.request.finished_at = timezone.now()
        self.request.save(update_fields=['status', 'finished_at', 'errors'])
        if self.csv_output_file:
            self.csv_output_file.close()
            # open the file in binary to upload to blob storage
            with open(self.csv_output_file_path, 'rb') as output_file:
                self.request.output_file.save(
                    os.path.basename(output_file.name),
                    output_file
                )
            # delete the output
            self.remove_csv_output_file()

    def on_update_progress(self, row, total_count):
        # save progress of task
        self.request.progress = (
            (row / total_count) * 100 if total_count else 0
        )
        self.request.save(update_fields=['progress'])

    def start(self):
        self.process_started()
        is_success = False
        error = None
        try:
            self.read_headers()
            self.process_headers()
            is_valid_headers = self.validate_headers()
            if not is_valid_headers:
                missing_headers = ', '.join(self.missing_columns)
                raise ValidationError(f'Missing headers: {missing_headers}')
            # open the output csv file
            self.csv_output_file_path = os.path.join(
                TEMP_OUTPUT_DIRECTORY,
                f'{str(self.request.uuid)}'
            ) + '.csv'
            # try to remove existing file if any
            self.remove_csv_output_file()
            # open the csv writer
            self.csv_output_file = open(self.csv_output_file_path, 'w')
            self.csv_output_writer = csv.writer(self.csv_output_file)
            # get output headers
            self.get_output_headers()
            self.csv_output_writer.writerow(self.output_headers)
            # process rows
            total_count, success_count, error_count = self.process_rows()
            if total_count == 0:
                raise ValidationError(
                    'You have uploaded empty spreadsheet, '
                    'please check again.'
                )
            is_success = True
            self.request.total_count = total_count
            self.request.success_count = success_count
            self.request.error_count = error_count
            # generate success notes
            if (
                self.request.success_count > 0 and
                self.request.error_count == 0
            ):
                self.request.success_notes = (
                    f'{self.request.success_count} entities have '
                    'been updated successfully.'
                )
            if (
                self.request.success_count > 0 and
                self.request.error_count > 0
            ):
                self.request.success_notes = (
                    f'{self.request.success_count} '
                    'entities have been updated successfully. '
                    f'{self.request.error_count} entities have errors.'
                )
            self.request.save(update_fields=[
                'total_count', 'success_count', 'error_count', 'success_notes'
            ])
        except Exception as ex:
            logger.error(ex)
            logger.error(traceback.format_exc())
            error = str(ex)
            is_success = False
        finally:
            self.process_ended(is_success, error)

    def read_headers(self):
        """Read column headers."""
        pass

    def process_headers(self):
        """Read headers."""
        if len(self.headers) == 0:
            raise RuntimeError('Headers are empty!')
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

    def process_rows(self):
        """Base process rows."""
        total_count = 0
        success_count = 0
        error_count = 0
        return total_count, success_count, error_count

    def get_output_headers(self):
        """Set output headers."""
        self.output_headers = [
            'Country',
            'Level',
            'Ucode',
            'Default Name',
            'Default Code'
        ]
        # add id fields
        for _, id_field in self.id_fields.items():
            field_name = id_field['field']
            self.output_headers.append(field_name)
        # add name fields
        for _, name_field in self.name_fields.items():
            field_name = name_field['field']
            self.output_headers.append(field_name)
        # add status and errors
        self.output_headers.append('Status')
        self.output_headers.append('Errors')

    def get_default_output_row(self, ucode):
        output_row = [
            '-' for i in range(len(self.output_headers))
        ]
        output_row[2] = ucode
        return output_row

    def get_output_row_with_status(self, output_row, is_success, error):
        """Set output row with status and error."""
        # status column should the last 2 index
        output_row[-2] = 'SUCCESS' if is_success else 'ERROR'
        if not is_success:
            output_row[-1] = error
        return output_row

    def update_output_row_with_entity(self, output_row,
                                      entity: GeographicalEntity):
        """Update output row with entity information."""
        output_row[0] = entity.ancestor.label if entity.ancestor else ''
        if entity.level == 0:
            output_row[0] = entity.label
        output_row[1] = entity.level
        output_row[3] = entity.label
        output_row[4] = entity.internal_code
        # return the output row and starting idx for id/name field
        return output_row, 5

    def process_row(self, row):
        """
        Process individual row.

        :param row: list of cell values
        :return: Tuple of is_success, updated_row
        """
        ucode = row[self.ucode_index]
        updated_row = self.get_default_output_row(ucode)
        try:
            # parse ucode
            unique_code, version_number = parse_unique_code(ucode)
        except ValueError as ex:
            return (
                False,
                self.get_output_row_with_status(updated_row, False, str(ex))
            )
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
            return (
                False,
                self.get_output_row_with_status(
                    updated_row, False, f'Entity {ucode} does not exist')
            )
        entity = entity.first()
        updated_row, new_idx_start = self.update_output_row_with_entity(
            updated_row, entity)
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
            # update output row
            updated_row[new_idx_start] = id_value
            new_idx_start += 1
            # validate non-empty value
            if id_value == '':
                continue
            # get the id_type
            id_type_in = id_field['idType']
            id_type = (
                [id for id in self.id_types if id.id == id_type_in['id']]
            )
            if len(id_type) == 0:
                id_errors.append(f'Invalid id type of {field_name}')
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
            # update output row
            updated_row[new_idx_start] = name_value
            new_idx_start += 1
            # validate non-empty value
            if name_value == '':
                continue
            # get the language
            lang_in = name_field['selectedLanguage']
            language = [lang for lang in self.languages if lang.id == lang_in]
            if len(language) == 0:
                name_errors.append(f'Invalid language of {field_name}')
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
            errors = []
            if id_errors:
                errors.append(', '.join(id_errors))
            if name_errors:
                errors.append(', '.join(name_errors))
            return (
                False,
                self.get_output_row_with_status(
                    updated_row, False, ', '.join(errors))
            )
        if id_warns:
            warns = ', '.join(id_warns)
            logger.warning(
                f'Processing new ids for {ucode} with warnings: {warns}')
        if name_warns:
            warns = ', '.join(name_warns)
            logger.warning(
                f'Processing new names for {ucode} with warnings: {warns}')
        if new_ids:
            EntityId.objects.bulk_create(new_ids)
        if new_names:
            EntityName.objects.bulk_create(new_names)
        return True, self.get_output_row_with_status(
            updated_row, True, None)

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

    def validate_input_file(self):
        """Validate input file from BatchEntityEdit obj."""
        self.read_headers()
        if self.total_rows < 1:
            return False, (
                'You have uploaded empty spreadsheet, '
                'please check again.'
            )
        if self.total_rows == 1:
            # contains only header
            return False, (
                'You have uploaded spreadsheet without any row, '
                'please check again.'
            )
        # check if has headers
        if len(self.headers) < 2:
            return False, (
                'You have uploaded spreadsheet with invalid headers, '
                'the headers must include ucode field and '
                'at least one ID/Name field, '
                'please check again.'
            )
        # store headers and total count
        self.request.total_count = self.total_rows
        self.request.headers = self.headers
        self.request.save(update_fields=['total_count', 'headers'])
        return True, None


class CSVBatchEntityEditImporter(BatchEntityEditBaseImporter):

    def read_headers(self):
        with self.request.input_file.open('r') as csv_file:
            file = csv_file.read().decode(
                'utf-8', errors='ignore').splitlines()
            csv_reader = csv.reader(file)
            self.headers = next(csv_reader)
            self.total_rows = sum(1 for row in csv_reader)

    def process_rows(self):
        success_count = 0
        error_count = 0
        line_count = 0
        with self.request.input_file.open('r') as csv_file:
            file = csv_file.read().decode(
                'utf-8', errors='ignore').splitlines()
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                    continue
                else:
                    is_row_success, output_row = self.process_row(row)
                    if is_row_success:
                        success_count += 1
                    else:
                        error_count += 1
                    self.csv_output_writer.writerow(output_row)
                self.on_update_progress(line_count, self.total_rows)
                line_count += 1
        return line_count - 1, success_count, error_count


class ExcelBatchEntityEditImporter(BatchEntityEditBaseImporter):

    def read_headers(self):
        self.headers = []
        with self.request.input_file.open('r') as excel_file:
            wb_obj = openpyxl.load_workbook(excel_file)
            sheet_obj = wb_obj.active
            max_col = sheet_obj.max_column
            self.total_rows = sheet_obj.max_row - 1
            # Loop will print all columns name
            for i in range(1, max_col + 1):
                cell_obj = sheet_obj.cell(row=1, column=i)
                self.headers.append(cell_obj.value)

    def process_rows(self):
        success_count = 0
        error_count = 0
        line_count = 0
        with self.request.input_file.open('r') as excel_file:
            wb_obj = openpyxl.load_workbook(excel_file)
            sheet_obj = wb_obj.active
            max_col = sheet_obj.max_column
            m_row = sheet_obj.max_row
            if m_row < 2:
                # contains only header or empty
                return line_count, success_count, error_count
            for row_idx in range(2, m_row + 1):
                row = []
                for col_idx in range(1, max_col + 1):
                    cell_obj = sheet_obj.cell(row=row_idx, column=col_idx)
                    row.append(cell_obj.value if cell_obj.value else '')
                is_row_success, output_row = self.process_row(row)
                if is_row_success:
                    success_count += 1
                else:
                    error_count += 1
                self.csv_output_writer.writerow(output_row)
                line_count += 1
                self.on_update_progress(line_count, self.total_rows)
        return line_count - 1, success_count, error_count


def get_entity_edit_importer(obj: BatchEntityEdit):
    if obj.input_file is None:
        raise RuntimeError('Batch session does not have input file uploaded!')
    if (
        obj.input_file.path.endswith('.xlsx') or
        obj.input_file.path.endswith('.xls')
    ):
        return ExcelBatchEntityEditImporter(obj)
    elif obj.input_file.path.endswith('.csv'):
        return CSVBatchEntityEditImporter(obj)
    return None
