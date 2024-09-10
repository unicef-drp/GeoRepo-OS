__author__ = 'zakki@kartoza.com'
__date__ = '29/08/23'
__copyright__ = ('Copyright 2023, Unicef')

import urllib.parse

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.upload_session import UploadSessionList
from dashboard.api_views.dataset import ValidationErrorCountryPreprosessing
from dashboard.models.entity_upload import REVIEWING, REJECTED
from dashboard.tests.model_factories import (
    EntityUploadF, LayerUploadSessionF
)
from georepo.tests.model_factories import (
    UserF, DatasetF,
    ModuleF, GeographicalEntityF
)


class TestUploadSessionList(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)
        self.creator = UserF.create()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=self.creator,
            status='Done'
        )
        self.upload_session_2 = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=self.creator,
            status='Reviewing'
        )
        self.upload_session_3 = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=self.creator,
            status='Pending'
        )

        geo_entity_1 = GeographicalEntityF(label='some-random-entity-1')
        geo_entity_2 = GeographicalEntityF(label='some-random-entity-2')

        for upload_session in [
            self.upload_session, self.upload_session_2, self.upload_session_3
        ]:
            EntityUploadF.create(
                upload_session=upload_session,
                status=REVIEWING,
                revised_geographical_entity=geo_entity_1
            )
            EntityUploadF.create(
                upload_session=upload_session,
                status=REJECTED,
                revised_geographical_entity=geo_entity_2
            )
            EntityUploadF.create(
                upload_session=upload_session,
                status=REVIEWING
            )

    def test_list_views(self):
        """
        Test Upload Session List without any parameter.
        """
        request = self.factory.post(
            reverse('upload-session-list')
        )
        request.user = self.superuser
        list_view = UploadSessionList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        all_ids = [upload['id'] for upload in response.data['results']]
        self.assertEqual(
            all_ids,
            [
                self.upload_session.id,
                self.upload_session_2.id,
                self.upload_session_3.id,
            ]
        )

    def test_sort(self):
        """
        Test sorting Upload Session List by ID descending.
        """
        query_params = {
            'sort_by': 'id',
            'sort_direction': 'desc'
        }
        request = self.factory.post(
            f"{reverse('upload-session-list')}?"
            f"{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = UploadSessionList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        all_ids = [upload['id'] for upload in response.data['results']]
        self.assertEqual(
            all_ids,
            [
                self.upload_session_3.id,
                self.upload_session_2.id,
                self.upload_session.id
            ]
        )

    def test_pagination(self):
        """
        Test Upload Session List pagination.
        """
        query_params = {
            'page': 2,
            'page_size': 1
        }
        request = self.factory.post(
            f"{reverse('upload-session-list')}?"
            f"{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = UploadSessionList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_page'], 3)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.upload_session_2.id
        )

    def test_search(self):
        """
        Test Upload Session List search.
        """
        request = self.factory.post(
            reverse('upload-session-list'),
            {
                'search_text': 'Revi'
            }
        )
        request.user = self.superuser
        list_view = UploadSessionList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.upload_session_2.id
        )

    def test_filter(self):
        """
        Test Upload Session List filter.
        """
        request = self.factory.post(
            reverse('upload-session-list'),
            {
                'status': [
                    self.upload_session_3.status
                ]
            }
        )
        request.user = self.superuser
        list_view = UploadSessionList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.upload_session_3.id
        )
        self.assertEqual(
            response.data['results'][0].get('level_0_entity'),
            'some-random-entity-1...'
        )

    def test_validation_error_step4(self):
        self.upload_session.validation_summaries = {
            "2": {
                "level": 2,
                "parent_missing": [
                    {
                        "level": 2,
                        "feature_id": 1,
                        "name": "Entity ABC",
                        "entity_id": "1",
                        "parent": None
                    }
                ],
                "parent_code_missing": [
                    {
                        "level": 2,
                        "feature_id": 1,
                        "name": "Entity ABC",
                        "entity_id": "1",
                        "parent": None
                    }
                ]
            }
        }
        self.upload_session.save()
        request = self.factory.get(
            reverse('dataset-country-validation') +
            f'?session={self.upload_session.id}'
        )
        request.user = self.superuser
        view = ValidationErrorCountryPreprosessing.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers['Content-Type'], 'text/html; charset=utf-8')
