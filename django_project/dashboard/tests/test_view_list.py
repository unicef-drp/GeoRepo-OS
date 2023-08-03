__author__ = 'zakki@kartoza.com'
__date__ = '31/07/23'
__copyright__ = ('Copyright 2023, Unicef')

import urllib.parse

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.views import (
    ViewList
)
from georepo.tests.model_factories import (
    UserF, DatasetF, DatasetViewF, ModuleF
)
from georepo.utils.permission import (
    grant_dataset_manager
)


class TestViewList(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.superuser = UserF.create(is_superuser=True)
        self.creator = UserF.create()
        self.dataset_view_1 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)

    def test_list_views(self):
        request = self.factory.post(
            reverse('view-list')
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.dataset_view_1.id
        )

        request = self.factory.post(
            reverse('view-list')
        )

        request.user = self.creator
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            self.dataset_view_1.id
        )

    def test_sort(self):
        dataset_view_2 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(dataset_view_2.dataset, self.creator)
        query_params = {
            'sort_by': 'id',
            'sort_direction': 'desc'
        }
        request = self.factory.post(
            f"{reverse('view-list')}?{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            dataset_view_2.id
        )
        self.assertEqual(
            response.data['results'][1].get('id'),
            self.dataset_view_1.id
        )

    def test_pagination(self):
        dataset_view_2 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(dataset_view_2.dataset, self.creator)
        query_params = {
            'page': 2,
            'page_size': 1
        }
        request = self.factory.post(
            f"{reverse('view-list')}?{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_page'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            dataset_view_2.id
        )

    def test_search(self):
        dataset_view_2 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(dataset_view_2.dataset, self.creator)
        request = self.factory.post(
            reverse('view-list'),
            {
                'search_text': dataset_view_2.description
            }
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            dataset_view_2.id
        )

    def test_filter(self):
        dataset_view_2 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(dataset_view_2.dataset, self.creator)
        request = self.factory.post(
            reverse('view-list'),
            {
                'dataset': [dataset_view_2.dataset.label],
                'min_privacy': [4],
            }
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            dataset_view_2.id
        )
