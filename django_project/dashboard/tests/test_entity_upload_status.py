import datetime
import json
import mock
from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from georepo.models import IdType
from georepo.tests.model_factories import (
    UserF, GeographicalEntityF, LanguageF, ModuleF, DatasetF
)
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    LayerFileF,
    EntityUploadF,
    EntityUploadChildLv1F
)
from dashboard.api_views.entity_upload_status import (
    EntityUploadStatusDetail,
    EntityUploadStatusList,
    EntityUploadLevel1List,
    OverlapsEntityUploadList,
    OverlapsEntityUploadDetail,
    RetriggerSingleValidation,
    EntityUploadStatusMetadata
)
from georepo.utils import absolute_path
from dashboard.models.entity_upload import PROCESSING_ERROR, STARTED


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_task(*args, **kwargs):
    return DummyTask('1')


class TestEntityUploadStatusApiViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.language = LanguageF.create()
        self.idType = IdType.objects.create(
            name='PCode'
        )
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module
        )

    def test_entity_upload_status_detail(self):
        entity_upload_status = EntityUploadF.create(
            comparison_data_ready=True
        )
        user = UserF.create(is_superuser=True)
        kwargs = {
            'id': entity_upload_status.id
        }
        request = self.factory.get(
            reverse('entity-upload-status-detail', kwargs=kwargs)
        )
        request.user = user
        view = EntityUploadStatusDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['comparison_ready'])

    def test_entity_upload_status_metadata(self):
        upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        upload_session.started_at = datetime.datetime(2023, 8, 14, 8, 8, 8)
        upload_session.save()
        entity_upload = EntityUploadF.create(
            upload_session=upload_session
        )
        entity_upload.started_at = datetime.datetime(2023, 8, 14, 10, 10, 10)
        entity_upload.save()
        user = UserF.create()
        request = self.factory.get(
            reverse('entity-upload-status-metadata') + f'/?id={upload_session.id}'
        )
        request.user = user
        view = EntityUploadStatusMetadata.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('ids', response.data)
        self.assertIn(entity_upload.id, response.data['ids'])
        self.assertIn('countries', response.data)
        self.assertIn(entity_upload.original_geographical_entity.label,
                      response.data['countries'])

    def test_entity_upload_status_list(self):
        upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        upload_session.started_at = datetime.datetime(2023, 8, 14, 8, 8, 8)
        upload_session.save()
        entity_upload = EntityUploadF.create(
            upload_session=upload_session
        )
        entity_upload.started_at = datetime.datetime(2023, 8, 14, 10, 10, 10)
        entity_upload.save()
        user = UserF.create()
        request = self.factory.post(
            reverse('entity-upload-status-list') + f'/?id={upload_session.id}',
            {
                'countries': [],
                'search_text': ''
            },
            format='json'
        )
        request.user = user
        view = EntityUploadStatusList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['results'],
            [
                {
                    'id': entity_upload.id,
                    'Adm0': entity_upload.original_geographical_entity.label,
                    'started at': '14 August 2023 10:10:10 UTC',
                    'status': 'Queued',
                    'error_summaries': None,
                    'error_report': '',
                    'is_importable': False,
                    'is_warning': False,
                    'progress': None,
                    'error_logs': None
                }
            ]
        )

    def test_entity_upload_level1_list(self):
        upload_session = LayerUploadSessionF.create()
        entity_upload = EntityUploadF.create(
            upload_session=upload_session
        )
        EntityUploadChildLv1F.create(
            entity_upload=entity_upload,
            entity_id='PAK_001',
            entity_name='Pakistan_001',
            parent_entity_id='PAK',
            overlap_percentage=100,
            feature_index=1
        )
        user = UserF.create()
        request = self.factory.get(
            reverse('entity-upload-level1-list') + f'/?id={entity_upload.id}'
        )
        request.user = user
        view = EntityUploadLevel1List.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_overlaps_entity_upload_list(self):
        upload_session = LayerUploadSessionF.create()
        test_file_path = (
            absolute_path(
                'georepo', 'tests',
                'geojson_dataset', 'damascus_qudsiya.geojson'
            )
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            level=1,
            parent_id_field='ADM0_PCODE',
            entity_type='Sub_district',
            name_fields=[
                {
                    'field': 'NAME_EN',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'PCODE',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
            layer_file=test_file_path
        )
        ancestor = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            label='Syria',
            internal_code='SY'
        )
        entity_upload_status = EntityUploadF.create(
            upload_session=upload_session,
            revised_geographical_entity=ancestor
        )
        with open(test_file_path) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                GeographicalEntityF.create(
                    dataset=upload_session.dataset,
                    level=1,
                    label=feature['properties']['NAME_EN'],
                    internal_code=feature['properties']['PCODE'],
                    geometry=GEOSGeometry(geom_str),
                    revision_number=1,
                    parent=ancestor,
                    layer_file=layer_file,
                    ancestor=ancestor
                )
        user = UserF.create()
        kwargs = {
            'upload_id': entity_upload_status.id
        }
        request = self.factory.get(
            reverse('fetch-entity-overlaps', kwargs=kwargs)
        )
        request.user = user
        view = OverlapsEntityUploadList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_overlaps_entity_upload_detail(self):
        upload_session = LayerUploadSessionF.create()
        ancestor = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            label='Syria',
            internal_code='SY'
        )
        EntityUploadF.create(
            upload_session=upload_session,
            revised_geographical_entity=ancestor
        )
        test_file_path = (
            absolute_path(
                'georepo', 'tests',
                'geojson_dataset', 'damascus_qudsiya.geojson'
            )
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            level=1,
            parent_id_field='ADM0_PCODE',
            entity_type='Sub_district',
            name_fields=[
                {
                    'field': 'NAME_EN',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'PCODE',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
            layer_file=test_file_path
        )
        geo_ids = []
        with open(test_file_path) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                geo = GeographicalEntityF.create(
                    dataset=upload_session.dataset,
                    level=1,
                    label=feature['properties']['NAME_EN'],
                    internal_code=feature['properties']['PCODE'],
                    geometry=GEOSGeometry(geom_str),
                    revision_number=1,
                    parent=ancestor,
                    layer_file=layer_file,
                    ancestor=ancestor
                )
                geo_ids.append(geo.id)
        user = UserF.create()
        kwargs = {
            'entity_id_1': geo_ids[0],
            'entity_id_2': geo_ids[1]
        }
        request = self.factory.get(
            reverse('fetch-entity-overlaps-detail', kwargs=kwargs)
        )
        request.user = user
        view = OverlapsEntityUploadDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('geometry_1', response.data)
        self.assertIn('geometry_2', response.data)
        self.assertIn('overlaps', response.data)
        self.assertIn('bbox', response.data)

    @mock.patch(
        'dashboard.api_views.entity_upload_status.'
        'validate_ready_uploads.apply_async'
    )
    def test_retrigger_single_validation(self, mocked_task):
        upload_session = LayerUploadSessionF.create()
        ancestor = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            label='Syria',
            internal_code='SY'
        )
        entity_upload_status = EntityUploadF.create(
            upload_session=upload_session,
            revised_geographical_entity=ancestor,
            status=PROCESSING_ERROR,
            logs='Test error'
        )
        mocked_task.side_effect = mocked_run_task
        user = UserF.create()
        kwargs = {
            'upload_id': entity_upload_status.id
        }
        request = self.factory.get(
            reverse('retrigger-single-upload-validation', kwargs=kwargs)
        )
        request.user = user
        view = RetriggerSingleValidation.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        entity_upload_status.refresh_from_db()
        self.assertEqual(entity_upload_status.status, STARTED)
        self.assertTrue(entity_upload_status.task_id)
        self.assertFalse(entity_upload_status.logs)
        self.assertFalse(entity_upload_status.summaries)
        self.assertFalse(entity_upload_status.error_report)
        mocked_task.assert_called_once()
