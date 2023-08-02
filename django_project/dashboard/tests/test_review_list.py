__author__ = 'zakki@kartoza.com'
__date__ = '31/07/23'
__copyright__ = ('Copyright 2023, Unicef')

import urllib.parse

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.reviews import ReviewList
from dashboard.models.entity_upload import REVIEWING, REJECTED
from dashboard.tests.model_factories import (
    EntityUploadF, LayerUploadSessionF
)
from georepo.tests.model_factories import (
    UserF, DatasetF,
    ModuleF
)


class TestReviewList(TestCase):

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
            uploader=self.creator
        )
        self.entity_upload_status_1 = EntityUploadF.create(
            upload_session=self.upload_session,
            status=REVIEWING
        )
        EntityUploadF.create(
            upload_session=self.upload_session,
            status=REJECTED
        )
        self.entity_upload_status_3 = EntityUploadF.create(
            upload_session=self.upload_session,
            status=REVIEWING
        )

    def test_list_views(self):
        """
        Test Review List without any parameter.
        It will return only entity_upload_status_1, as only those with status
        REVIEWING or APPROVED will be returned.
        """
        request = self.factory.post(
            reverse('review-list')
        )
        request.user = self.superuser
        list_view = ReviewList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.entity_upload_status_1.id
        )
        self.assertEqual(
            response.data['results'][1].get('id'),
            self.entity_upload_status_3.id
        )

        request = self.factory.post(
            reverse('view-list')
        )

    def test_sort(self):
        """
        Test sorting Review List by ID descending.
        """
        query_params = {
            'sort_by': 'id',
            'sort_direction': 'desc'
        }
        request = self.factory.post(
            f"{reverse('review-list')}?{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ReviewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.entity_upload_status_3.id
        )
        self.assertEqual(
            response.data['results'][1].get('id'),
            self.entity_upload_status_1.id
        )

    def test_pagination(self):
        """
        Test Review List pagination.
        """
        query_params = {
            'page': 2,
            'page_size': 1
        }
        request = self.factory.post(
            f"{reverse('review-list')}?{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ReviewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_page'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.entity_upload_status_3.id
        )

    def test_search(self):
        """
        Test Review List search.
        """
        entity_upload_status_3 = EntityUploadF.create(
            upload_session=self.upload_session,
            status=REVIEWING,
            logs='Some logs'
        )
        request = self.factory.post(
            reverse('review-list'),
            {
                'search_text': entity_upload_status_3.logs
            }
        )
        request.user = self.superuser
        list_view = ReviewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            entity_upload_status_3.id
        )

    def test_filter(self):
        """
        Test Review List filter.
        """
        request = self.factory.post(
            reverse('review-list'),
            {
                'dataset': [self.entity_upload_status_3.upload_session.dataset.label]
            }
        )
        request.user = self.superuser
        list_view = ReviewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.entity_upload_status_1.id
        )
        self.assertEqual(
            response.data['results'][1].get('id'),
            self.entity_upload_status_3.id
        )
