import copy
import uuid
import json
from dateutil.parser import isoparse
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.test import APIRequestFactory

from georepo.utils import absolute_path
from georepo.models import IdType
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from dashboard.api_views.entity import EntityEdit


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
            'names': [
                {
                    'id': self.geographical_entity_name_1.id,
                    'default': True,
                    'name': self.geographical_entity_name_1.name,
                    'language_id': self.geographical_entity_name_1.language_id
                },
                {
                    'id': self.geographical_entity_name_2.id,
                    'default': False,
                    'name': self.geographical_entity_name_2.name,
                    'language_id': self.geographical_entity_name_2.language_id
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

    def test_entity_edit_insufficient_permission_get(self):
        user = UserF.create()
        request = self.factory.get(
            f"{reverse('entity-edit', args=[self.entity.id])}/"
        )
        request.user = user
        edit_view = EntityEdit.as_view()
        response = edit_view(request, self.entity.id)
        self.assertEqual(response.data, {'detail': 'Insufficient permission'})

    def test_entity_edit_insufficient_permission_post(self):
        user = UserF.create()
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.entity.id])}/"
        )
        request.user = user
        edit_view = EntityEdit.as_view()
        response = edit_view(request, self.entity.id)
        self.assertEqual(response.data, {'detail': 'Insufficient permission'})

    def test_entity_edit_get(self):
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
            'label': self.geographical_entity_name_1.name,
            'names': [
                {
                    'id': self.geographical_entity_name_1.id,
                    'default': True,
                    'name': self.geographical_entity_name_1.name,
                    'language_id': self.geographical_entity_name_1.language_id
                },
                {
                    'id': self.geographical_entity_name_2.id,
                    'default': False,
                    'name': self.geographical_entity_name_2.name,
                    'language_id': self.geographical_entity_name_2.language_id
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
        self.assertEqual(
            self._convert_response_to_dict(response.data),
            expected_response
        )

    def test_entity_edit_source_type_privacy(self):
        payload = copy.deepcopy(self.payload)
        payload['source'] = 'Source_1'
        payload['privacy_level'] = 3
        payload['type'] = 'Province'
        request = self.factory.post(
            f"{reverse('entity-edit', args=[self.geographical_entity.id])}/",
            json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.superuser
        list_view = EntityEdit.as_view()
        response = list_view(request, self.geographical_entity.id)
        self.assertEqual(
            self._convert_response_to_dict(response.data),
            payload
        )

    def test_entity_edit_add_name(self):
        payload = copy.deepcopy(self.payload)
        payload['names'].append({
            'id': 0,
            'default': False,
            'name': 'some-name',
            'language_id': None
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
        self.assertNotEqual(
            self._convert_response_to_dict(response.data)['names'][-1]['id'],
            0
        )

    def test_entity_edit_change_name(self):
        payload = copy.deepcopy(self.payload)
        payload['names'][0] = {
            'id': payload['names'][0]['id'],
            'default': True,
            'name': f"{payload['names'][0]['name']}-updated",
            'language_id': payload['names'][0]['language_id']
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

    def test_entity_edit_remove_name(self):
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

    def test_entity_edit_add_code(self):
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
        self.assertEqual(
            self._convert_response_to_dict(
                response.data
            )['codes'][-1]['value'],
            'some-code'
        )
        self.assertNotEqual(
            self._convert_response_to_dict(
                response.data
            )['codes'][-1]['value'],
            0
        )

    def test_entity_edit_change_code(self):
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

    def test_entity_edit_remove_code(self):
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
