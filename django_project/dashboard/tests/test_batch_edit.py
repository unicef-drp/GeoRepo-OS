import json
import random
import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from dateutil.parser import isoparse
from georepo.utils import absolute_path
from georepo.models import IdType, EntityId, EntityName
from georepo.models.base_task_request import (
    PENDING, DONE
)
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from dashboard.models.batch_edit import BatchEntityEdit
from dashboard.api_views.entity import (
    BatchEntityEditAPI,
    BatchEntityEditFile,
    BatchEntityEditResultAPI
)
from dashboard.tools.entity_edit import (
    get_entity_edit_importer
)


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process_batch_job(*args, **kwargs):
    return DummyTask('1')


XLSX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.sheet'
)


class TestBatchEdit(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanish'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.id_1 = IdType.objects.create(name='id_1')
        self.id_2 = IdType.objects.create(name='id_2')
        self.entity_type0 = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            geom = GEOSGeometry(geom_str)
            self.pak0_1 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type0,
                is_validated=True,
                is_approved=True,
                is_latest=False,
                geometry=geom,
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=1,
                start_date=isoparse('2023-01-01T06:16:13Z'),
                end_date=isoparse('2023-01-10T06:16:13Z'),
                concept_ucode='#PAK_1',
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.pak0_1,
                default=True,
                value=self.pak0_1.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.pak0_1,
                name=self.pak0_1.label,
                language=self.enLang,
                idx=0
            )
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_1.geojson')
        with open(geojson_1_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entities_1 = []
            self.entities_2 = []
            v1_idx = [0, 1]
            random.shuffle(v1_idx)
            temp_entities = {}
            for i in v1_idx:
                geom = GEOSGeometry(geom_str)
                entity = GeographicalEntityF.create(
                    parent=self.pak0_1,
                    ancestor=self.pak0_1,
                    level=1,
                    admin_level_name='Region',
                    dataset=self.dataset,
                    type=self.entity_type0,
                    is_validated=True,
                    is_approved=True,
                    is_latest=False,
                    geometry=geom,
                    internal_code=f'PAK00{i+1}',
                    revision_number=1,
                    label='Khyber Pakhtunkhwa',
                    unique_code=f'PAK_000{i+1}',
                    unique_code_version=1,
                    start_date=isoparse('2023-01-01T06:16:13Z'),
                    end_date=isoparse('2023-01-10T06:16:13Z'),
                    concept_ucode=f'#PAK_{i+2}',
                    centroid=geom.point_on_surface.wkt,
                    bbox='[' + ','.join(map(str, geom.extent)) + ']'
                )
                EntityIdF.create(
                    code=self.pCode,
                    geographical_entity=entity,
                    default=True,
                    value=entity.internal_code
                )
                EntityNameF.create(
                    geographical_entity=entity,
                    name=entity.label,
                    language=self.enLang,
                    idx=0
                )
                temp_entities[i] = entity
            v1_idx.sort()
            self.entities_1 = [temp_entities[i] for i in v1_idx]

    def do_test_importer(self, file):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now(),
            input_file=file,
            ucode_field='ucode',
            id_fields=[
                {
                    "id": "1",
                    "field": "id_1",
                    "idType": {
                        "id": self.id_1.id,
                        "name": self.id_1.name
                    },
                    "default": False
                },
                {
                    "id": "2",
                    "field": "id_2",
                    "idType": {
                        "id": self.id_2.id,
                        "name": self.id_2.name
                    },
                    "default": False
                }
            ],
            name_fields=[
                {
                    "id": "1",
                    "field": "name_1",
                    "label": "",
                    "default": False,
                    "duplicateError": False,
                    "selectedLanguage": self.enLang.id
                },
                {
                    "id": "2",
                    "field": "name_2",
                    "label": "",
                    "default": False,
                    "duplicateError": False,
                    "selectedLanguage": self.esLang.id
                }
            ]
        )
        importer = get_entity_edit_importer(batch_edit, False)
        importer.start()
        batch_edit.refresh_from_db()
        self.assertEqual(batch_edit.status, DONE)
        self.assertTrue(batch_edit.success_notes)
        self.assertFalse(batch_edit.errors)
        self.assertEqual(batch_edit.total_count, 1)
        self.assertEqual(batch_edit.success_count, 1)
        self.assertEqual(batch_edit.error_count, 0)
        self.assertTrue(EntityId.objects.filter(
            geographical_entity=self.pak0_1,
            code=self.id_1
        ).exists())
        self.assertTrue(EntityId.objects.filter(
            geographical_entity=self.pak0_1,
            code=self.id_2
        ).exists())
        self.assertEqual(EntityName.objects.filter(
            geographical_entity=self.pak0_1
        ).count(), 3)

    def test_import_csv(self):
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.csv')
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name='import_valid_file.csv',
                content_type='text/csv')
        self.do_test_importer(file)

    def test_import_excel(self):
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.xlsx')
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name='import_valid_file.xlsx',
                content_type=XLSX_CONTENT_TYPE)
        self.do_test_importer(file)

    def test_create_batch_entity_edit(self):
        request = self.factory.put(
            reverse('batch-entity-edit') +
            f'?dataset_id={self.dataset.id}'
        )
        request.user = self.superuser
        view = BatchEntityEditAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        batch_id = response.data['id']
        batch_edit = BatchEntityEdit.objects.filter(id=batch_id).first()
        self.assertTrue(batch_edit)

    def test_fetch_batch_entity_edit(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        request = self.factory.get(
            reverse('batch-entity-edit') +
            f'?dataset_id={self.dataset.id}'
        )
        request.user = self.superuser
        view = BatchEntityEditAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], batch_edit.id)
        request = self.factory.get(
            reverse('batch-entity-edit') +
            f'?dataset_id={self.dataset.id}&batch_edit_id={batch_edit.id}'
        )
        request.user = self.superuser
        view = BatchEntityEditAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], batch_edit.id)

    @mock.patch(
        'dashboard.api_views.entity.'
        'process_batch_entity_edit.delay',
        mock.Mock(side_effect=mocked_process_batch_job)
    )
    def test_update_batch_entity_edit(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        data = {
            'preview': True,
            'batch_edit_id': batch_edit.id,
            'ucode_field': 'test_field1',
            'name_fields': [
                {
                    'field': 'name_0',
                    'selectedLanguage': self.enLang.id
                }
            ],
            'id_fields': [
                {
                    'field': 'code_0',
                    'idType': {
                        'id': self.id_1.id
                    }
                }
            ]
        }
        request = self.factory.post(
            reverse('batch-entity-edit'), data=data, format='json'
        )
        request.user = self.superuser
        view = BatchEntityEditAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        batch_edit.refresh_from_db()
        self.assertEqual(batch_edit.ucode_field, data['ucode_field'])
        self.assertEqual(batch_edit.name_fields, data['name_fields'])
        self.assertEqual(batch_edit.id_fields, data['id_fields'])

    def run_upload_file(self, test_file_path, test_file_name,
                        content_type, batch_edit):
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name=test_file_name,
                content_type=content_type)
        request = self.factory.post(
            reverse(
                'batch-entity-edit-file'
            ),
            data={
                'file': file,
                'batch_edit_id': batch_edit.id
            }
        )
        request.user = self.superuser
        view = BatchEntityEditFile.as_view()
        return view(request)

    def test_upload_csv_file(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_empty.csv')
        response = self.run_upload_file(test_file_path, 'import_empty.csv',
                                        'text/csv', batch_edit)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'],
                         'You have uploaded empty spreadsheet, '
                         'please check again.')
        batch_edit.refresh_from_db()
        self.assertTrue(batch_edit.input_file)
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.csv')
        response = self.run_upload_file(test_file_path,
                                        'import_valid_file.csv',
                                        'text/csv', batch_edit)
        self.assertEqual(response.status_code, 204)
        batch_edit.refresh_from_db()
        self.assertTrue(batch_edit.input_file)
        self.assertTrue(batch_edit.headers)
        self.assertEqual(batch_edit.total_count, 1)

    def test_upload_excel_file(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_empty.xlsx')
        response = self.run_upload_file(test_file_path, 'import_empty.xlsx',
                                        XLSX_CONTENT_TYPE, batch_edit)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'],
                         'You have uploaded empty spreadsheet, '
                         'please check again.')
        batch_edit.refresh_from_db()
        self.assertTrue(batch_edit.input_file)
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.xlsx')
        response = self.run_upload_file(test_file_path,
                                        'import_valid_file.xlsx',
                                        XLSX_CONTENT_TYPE, batch_edit)
        self.assertEqual(response.status_code, 204)
        batch_edit.refresh_from_db()
        self.assertTrue(batch_edit.input_file)
        self.assertTrue(batch_edit.headers)
        self.assertEqual(batch_edit.total_count, 1)

    def test_remove_excel_file(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.xlsx')
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name='import_valid_file.xlsx',
                content_type=XLSX_CONTENT_TYPE)
        batch_edit.input_file = file
        batch_edit.save(update_fields=['input_file'])
        request = self.factory.delete(
            reverse('batch-entity-edit-file') +
            f'?batch_edit_id={batch_edit.id}'
        )
        request.user = self.superuser
        view = BatchEntityEditFile.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 204)
        batch_edit.refresh_from_db()
        self.assertFalse(batch_edit.input_file)
        self.assertFalse(batch_edit.headers)
        self.assertEqual(batch_edit.total_count, 0)

    def test_fetch_result(self):
        batch_edit = BatchEntityEdit.objects.create(
            dataset=self.dataset,
            status=PENDING,
            submitted_by=self.superuser,
            submitted_on=timezone.now()
        )
        request = self.factory.get(
            reverse('batch-entity-edit-result') +
            f'?batch_edit_id={batch_edit.id}&preview=false'
        )
        request.user = self.superuser
        view = BatchEntityEditResultAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 400)
        batch_edit.status = DONE
        test_file_path = absolute_path(
            'dashboard', 'tests',
            'importer_data', 'import_valid_file.csv')
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name='import_valid_file.csv',
                content_type='text/csv')
        batch_edit.output_file = file
        batch_edit.save(update_fields=['output_file', 'status'])
        request = self.factory.get(
            reverse('batch-entity-edit-result') +
            f'?batch_edit_id={batch_edit.id}&preview=false'
        )
        request.user = self.superuser
        view = BatchEntityEditResultAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ucode'], 'PAK_V1')
