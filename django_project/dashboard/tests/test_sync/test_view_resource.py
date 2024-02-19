__author__ = 'zakki@kartoza.com'
__date__ = '19/09/23'
__copyright__ = ('Copyright 2023, Unicef')

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.view_sync import ViewResourcesSyncList
from georepo.tests.model_factories import (
    UserF, DatasetF, DatasetViewF,
    ModuleF
)
from georepo.models.dataset_view import DatasetViewResource
from georepo.utils.permission import (
    grant_dataset_manager
)


class TestViewResourceSyncList(TestCase):

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
        self.dsv_resources_1 = DatasetViewResource.objects.get(
            privacy_level=4,
            dataset_view=self.dataset_view_1
        )
        self.dsv_resources_1.entity_count = 10
        self.dsv_resources_1.save()
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)

    def test_list_view_resource(self):
        """
        Test list only Dataset View Resource with entity count > 0.
        """
        request = self.factory.get(
            reverse('view-resource-sync-list', args=[self.dataset_view_1.id])
        )
        request.user = self.superuser
        list_view = ViewResourcesSyncList.as_view()
        response = list_view(request, self.dataset_view_1.id)
        expected_result = {
            'centroid_size': '0B',
            'centroid_sync_progress': 0.0,
            'centroid_sync_status': 'out_of_sync',
            'id': self.dsv_resources_1.id,
            'uuid': str(self.dsv_resources_1.uuid),
            'privacy_level': 4,
            'vector_tile_sync_status': 'out_of_sync',
            'vector_tiles_progress': 0.0,
            'vector_tiles_size': '0B',
        }
        self.assertEqual(
            len(response.data),
            1
        )
        self.assertEqual(
            dict(response.data[0]),
            expected_result
        )
