__author__ = 'zakki@kartoza.com'
__date__ = '19/09/23'
__copyright__ = ('Copyright 2023, Unicef')

import urllib.parse

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.view_sync import ViewSyncList
from georepo.tests.model_factories import (
    UserF, DatasetF, DatasetViewF, ModuleF
)
from georepo.utils.permission import (
    grant_dataset_manager
)


class TestViewSyncList(TestCase):

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
            dataset=self.dataset,
            created_by=self.creator
        )
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)

    def test_list_views(self):
        request = self.factory.post(
            reverse('view-sync-list-per-dataset', args=[self.dataset.id])
        )
        request.user = self.superuser
        list_view = ViewSyncList.as_view()
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
            reverse('view-sync-list-per-dataset', args=[self.dataset.id])
        )

        request.user = self.creator
        list_view = ViewSyncList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        expected_result = {
            'id': self.dataset_view_1.id,
            'dataset': self.dataset_view_1.dataset_id,
            'name': self.dataset_view_1.name,
            'is_tiling_config_match': True,
            'vector_tile_sync_status': 'synced',
            'product_sync_status': 'synced',
            'simplification_status': 'out_of_sync',
            'simplification_progress': 0.0,
            'vector_tiles_progress': 0.0,
            'product_progress': 0.0,
            'permissions': ['Manage', 'Read']
        }
        self.assertEqual(
            dict(response.data['results'][0]),
            expected_result
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
            f"{reverse('view-sync-list-per-dataset', args=[self.dataset.id])}?"
            f"{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ViewSyncList.as_view()
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
            f"{reverse('view-sync-list-per-dataset', args=[self.dataset.id])}"
            f"?{urllib.parse.urlencode(query_params)}"
        )
        request.user = self.superuser
        list_view = ViewSyncList.as_view()
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
            reverse('view-sync-list-per-dataset', args=[self.dataset.id]),
            {
                'search_text': dataset_view_2.description
            }
        )
        request.user = self.superuser
        list_view = ViewSyncList.as_view()
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
            reverse('view-sync-list-per-dataset', args=[self.dataset.id]),
            {
                'dataset': [
                    dataset_view_2.dataset.label,
                    dataset_view_2.dataset.uuid,
                    dataset_view_2.dataset_id,
                ],
                'min_privacy': [4],
            }
        )
        request.user = self.superuser
        list_view = ViewSyncList.as_view()
        response = list_view(request)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_page'], 1)
        self.assertEqual(
            response.data['results'][0].get('id'),
            dataset_view_2.id
        )
