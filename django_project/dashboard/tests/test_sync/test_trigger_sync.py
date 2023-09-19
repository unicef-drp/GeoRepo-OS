__author__ = 'zakki@kartoza.com'
__date__ = '19/09/23'
__copyright__ = ('Copyright 2023, Unicef')

from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.view_sync import SynchronizeView
from georepo.tests.model_factories import (
    UserF, DatasetF, DatasetViewF, ModuleF
)
from georepo.utils.permission import (
    grant_dataset_manager
)
from georepo.models.dataset_tile_config import AdminLevelTilingConfig
from georepo.models.dataset_view_tile_config import ViewAdminLevelTilingConfig
from georepo.models.dataset_view import DatasetView, DatasetViewResource


@override_settings(CELERY_ALWAYS_EAGER=True, BROKER_BACKEND='memory',
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class TestTrigegrSync(TestCase):

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
        self.dsv_resources_2 = DatasetViewResource.objects.get(
            privacy_level=3,
            dataset_view=self.dataset_view_1
        )
        self.dsv_resources_2.entity_count = 5
        self.dsv_resources_2.save()
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)

    def test_sync_all(self):
        request = self.factory.post(
            reverse('sync-view'),
            {
                'sync_options': ['tiling_config', 'vector_tiles', 'products'],
                'view_ids': [
                    self.dataset_view_1.id
                ],
            }
        )
        request.user = self.superuser
        list_view = SynchronizeView.as_view()
        list_view(request)
        self.dataset_view_1.refresh_from_db()
        self.assertEqual(
            self.dataset_view_1.product_sync_status,
            DatasetView.SyncStatus.SYNCING
        )
        self.assertEqual(
            self.dataset_view_1.product_progress,
            0
        )
        self.assertEqual(
            self.dataset_view_1.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCING
        )
        self.assertEqual(
            self.dataset_view_1.vector_tiles_progress,
            0
        )
