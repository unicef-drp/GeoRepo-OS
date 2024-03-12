import copy
import uuid
import json
from unittest import mock
from dateutil.parser import isoparse
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.test import APIRequestFactory

from georepo.utils import absolute_path
from georepo.models import IdType, EntityName, DatasetView
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    init_view_privacy_level,
    calculate_entity_count_in_view
)
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from dashboard.api_views.entity import EntityEdit, CountrySearchAPI
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    EntityUploadF,
)


@mock.patch(
    'dashboard.tasks.review.check_affected_dataset_views.delay'
)
class TestApiEntity(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanist'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.create(name='PCode')
        self.iso3cd = IdType.objects.create(name='ISO3DC')
        self.entity_type = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
        self.entity = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=self.entity_type,
            level=0,
            dataset=self.dataset,
            internal_code='GO',
            label='GO',
            is_approved=True,
            is_latest=True,
            unique_code='GO',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#GO_1'
        )
        self.factory = APIRequestFactory()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geographical_entity = GeographicalEntityF.create(
                dataset=self.dataset,
                type=self.entity_type,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                start_date=isoparse('2023-01-01T06:16:13Z'),
                concept_ucode='#PAK_1'
            )
            self.geographical_entity_code_1 = EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.geographical_entity,
                default=True,
                value=self.geographical_entity.internal_code
            )
            self.geographical_entity_code_2 = EntityIdF.create(
                code=self.iso3cd,
                geographical_entity=self.geographical_entity,
                default=False,
                value='some-code'
            )
            self.geographical_entity_name_1 = EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name=self.geographical_entity.label,
                language=self.enLang,
                idx=0
            )
            self.geographical_entity_name_2 = EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name='only paktang',
                default=False,
                language=self.esLang,
                idx=1
            )
        self.payload = {
            'id': self.geographical_entity.id,
            'source': None,
            'type': 'Country',
            'privacy_level': 4,
            'label': self.geographical_entity_name_1.name,
            'is_dirty': True,
            'names': [
                {
                    'id': self.geographical_entity_name_1.id,
                    'default': True,
                    'name': self.geographical_entity_name_1.name,
                    'language_id': self.geographical_entity_name_1.language_id,
                    'label': ''
                },
                {
                    'id': self.geographical_entity_name_2.id,
                    'default': False,
                    'name': self.geographical_entity_name_2.name,
                    'language_id': self.geographical_entity_name_2.language_id,
                    'label': ''
                },
            ],
            'codes': [
                {
                    'id': self.geographical_entity_code_1.id,
                    'default': True,
                    'value': self.geographical_entity_code_1.value,
                    'code_id': self.geographical_entity_code_1.code_id
                }
            ]
        }

    def _convert_response_to_dict(self, response_data):
        response_data['names'] = [
            dict(name) for name in response_data['names']
        ]
        response_data['codes'] = [
            dict(code) for code in response_data['codes']
        ]
        return response_data

    def test_entity_edit_insufficient_permission_get(self, mock_check_views):
        user = UserF.create()
        request = self.factory.get(
            f"{reverse('entity-edit', args=[self.entity.id])}/"
        )
        request.user = user
        edit_view = EntityEdit.as_view()
        response = edit_view(request, self.entity.id)
        self.assertEqual(response.data, {'detail': 'Insufficient permission'})

    def test_entity_edit_insufficient_permission_post(self, mock_check_views):
        user = UserF.create()
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.entity.id])}/"
        )
        request.user = user
        edit_view = EntityEdit.as_view()
        response = edit_view(request, self.entity.id)
        self.assertEqual(response.data, {'detail': 'Insufficient permission'})
        mock_check_views.assert_not_called()

    def test_entity_edit_get(self, mock_check_views):
        from django.core.cache import cache
        cache.clear()
        request = self.factory.get(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/"
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        expected_response = {
            'id': self.geographical_entity.id,
            'source': None,
            'type': 'Country',
            'privacy_level': 4,
            'is_dirty': False,
            'label': self.geographical_entity_name_1.name,
            'names': [
                {
                    'id': self.geographical_entity_name_1.id,
                    'default': True,
                    'name': self.geographical_entity_name_1.name,
                    'language_id': self.geographical_entity_name_1.language_id,
                    'label': self.geographical_entity_name_1.label
                },
                {
                    'id': self.geographical_entity_name_2.id,
                    'default': False,
                    'name': self.geographical_entity_name_2.name,
                    'language_id': self.geographical_entity_name_2.language_id,
                    'label': self.geographical_entity_name_2.label
                },
            ],
            'codes': [
                {
                    'id': self.geographical_entity_code_1.id,
                    'default': True,
                    'value': self.geographical_entity_code_1.value,
                    'code_id': self.geographical_entity_code_1.code_id
                },
                {
                    'id': self.geographical_entity_code_2.id,
                    'default': False,
                    'value': self.geographical_entity_code_2.value,
                    'code_id': self.geographical_entity_code_2.code_id
                }
            ]
        }
        print(response.data)
        self.assertEqual(
            self._convert_response_to_dict(response.data),
            expected_response
        )
        mock_check_views.assert_not_called()

    def test_entity_edit_source_type_privacy(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['source'] = 'Source_1'
        payload['privacy_level'] = 3
        payload['type'] = 'Province'
        payload['is_dirty'] = True
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        payload['is_dirty'] = False
        self.assertEqual(
            self._convert_response_to_dict(response.data),
            payload
        )
        mock_check_views.assert_called()

    def test_entity_edit_add_name(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['names'].append({
            'id': 0,
            'default': False,
            'name': 'some-name',
            'language_id': None,
            'label': ''
        })
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(
            self._convert_response_to_dict(response.data)['names'][-1]['name'],
            'some-name'
        )
        name_id = (
            self._convert_response_to_dict(response.data)['names'][-1]['id']
        )
        self.assertNotEqual(name_id, 0)
        mock_check_views.assert_called()
        name = EntityName.objects.get(id=name_id)
        # idx should be positive integer
        self.assertTrue(name.idx is not None and name.idx > 0)

    def test_entity_edit_change_name(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['names'][0] = {
            'id': payload['names'][0]['id'],
            'default': True,
            'name': f"{payload['names'][0]['name']}-updated",
            'language_id': payload['names'][0]['language_id'],
            'label': ''
        }
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(
            self._convert_response_to_dict(response.data)['names'][0]['name'],
            'Pakistan-updated'
        )
        mock_check_views.assert_called()
        name = EntityName.objects.get(id=payload['names'][0]['id'])
        # idx should be positive integer
        self.assertTrue(name.idx is not None and name.idx == 0)

    def test_entity_edit_remove_name(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['names'] = payload['names'][:1]
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(len(response.data['names']), 1)
        mock_check_views.assert_called()

    def test_entity_edit_add_code(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['codes'].append({
            'id': 0,
            'default': False,
            'value': 'some-code',
            'code_id': self.geographical_entity_code_1.code_id
        })
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        response_data = self._convert_response_to_dict(
            response.data
        )
        self.assertEqual(
            response_data['codes'][-1]['value'],
            'some-code'
        )
        self.assertNotEqual(
            response_data['codes'][-1]['value'],
            0
        )
        mock_check_views.assert_called()

    def test_entity_edit_change_code(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['codes'][0] = {
            'id': payload['codes'][0]['id'],
            'default': True,
            'value': f"{payload['codes'][0]['value']}-updated",
            'code_id': payload['codes'][0]['code_id']
        }
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(
            self._convert_response_to_dict(response.data)['codes'][0]['value'],
            'PAK-updated'
        )
        mock_check_views.assert_called()

    def test_entity_edit_remove_code(self, mock_check_views):
        payload = copy.deepcopy(self.payload)
        payload['codes'] = payload['codes'][:1]
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(len(response.data['codes']), 1)
        mock_check_views.assert_called()

    def test_country_search_in_dataset(self, mock_check_views):
        kwargs = {
            'object_type': 'dataset'
        }
        request = self.factory.get(
            reverse(
                'country-search',
                kwargs=kwargs
            ) + f'?dataset_id={self.dataset.id}&search_text=go'
        )
        request.user = self.superuser
        view = CountrySearchAPI.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('countries', response.data)
        self.assertEqual(len(response.data['countries']), 1)

    def test_country_search_in_view(self, mock_check_views):
        generate_default_view_dataset_latest(self.dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(dataset_view)
        calculate_entity_count_in_view(dataset_view)
        kwargs = {
            'object_type': 'view'
        }
        request = self.factory.get(
            reverse(
                'country-search',
                kwargs=kwargs
            ) + f'?view_id={dataset_view.id}&search_text=go'
        )
        request.user = self.superuser
        view = CountrySearchAPI.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('countries', response.data)
        self.assertEqual(len(response.data['countries']), 1)

    def test_country_search_in_upload_session(self, mock_check_views):
        upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        EntityUploadF.create(
            upload_session=upload_session,
            status='Valid',
            original_geographical_entity=self.entity
        )
        kwargs = {
            'object_type': 'upload_session'
        }
        request = self.factory.get(
            reverse(
                'country-search',
                kwargs=kwargs
            ) + f'?session_id={upload_session.id}&search_text=go'
        )
        request.user = self.superuser
        view = CountrySearchAPI.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('countries', response.data)
        self.assertEqual(len(response.data['countries']), 1)
