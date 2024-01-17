import json

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from georepo.models import (
    DatasetView, DatasetViewResource
)
from georepo.tasks.dataset_view import check_affected_dataset_views
from georepo.tests.model_factories import (
    ModuleF
)
from georepo.tests.model_factories import (
    UserF,
    DatasetF,
    GeographicalEntityF,
    EntityTypeF,
    DatasetViewF
)
from georepo.utils import absolute_path
from georepo.utils.dataset_view import (
    create_sql_view,
    init_view_privacy_level,
    calculate_entity_count_in_view
)
from georepo.utils.permission import (
    grant_dataset_manager
)
from modules.admin_boundaries.review import generate_default_views


class TestCheckAffectedViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.user_1 = UserF.create(username='test_1')
        self.dataset_1 = DatasetF.create()
        grant_dataset_manager(self.dataset_1, self.user_1)
        self.entity_type = EntityTypeF.create(label='Country')
        geojson_0_1_path = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset', 'level_0_1.geojson')
        with open(geojson_0_1_path) as geojson:
            data = json.load(geojson)
        geom_str = json.dumps(data['features'][0]['geometry'])
        self.geographical_entity = GeographicalEntityF.create(
            dataset=self.dataset_1,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            geometry=GEOSGeometry(geom_str),
            internal_code='PAK',
            revision_number=1
        )
        self.superuser = UserF.create(is_superuser=True)
        self.creator = UserF.create()
        generate_default_views(self.dataset_1)
        self.dataset_view_1 = DatasetViewF.create(
            name='custom',
            created_by=self.creator,
            dataset=self.dataset_1,
            product_sync_status=DatasetView.SyncStatus.SYNCED,
            vector_tile_sync_status=DatasetView.SyncStatus.SYNCED,
            is_static=False,
            query_string=(
                f'select * from georepo_geographicalentity where '
                f'dataset_id={self.dataset_1.id}'
            )
        )
        views = DatasetView.objects.filter(
            dataset=self.dataset_1
        )
        for view in views:
            create_sql_view(view)
            init_view_privacy_level(view)
            # init view entity count
            calculate_entity_count_in_view(view)
            resources = DatasetViewResource.objects.filter(
                dataset_view=view,
                entity_count__gt=0
            )
            for resource in resources:
                resource.set_synced(vector_tiles=True, product=True)
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)
        self.dataset_view_1.refresh_from_db()

    def test_affect_all_view_1_entity(self):
        """
        Test Dataset View containing specific entity. All Dataset View
        contains this entity. Checking uses 1 entity.
        """
        self.assertEqual(
            self.dataset_view_1.product_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.assertEqual(
            self.dataset_view_1.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        check_affected_dataset_views(
            dataset_id=self.dataset_1.id,
            entity_id=[self.geographical_entity.id]
        )

        for dataset_view in DatasetView.objects.filter(dataset=self.dataset_1):
            self.assertEqual(
                dataset_view.dataset.sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.product_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.vector_tile_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )

    def test_affect_all_view_unique_code(self):
        """
        Test Dataset View containing specific entity. All Dataset View
        contains this entity. Checking uses unique_codes
        """
        self.assertEqual(
            self.dataset_view_1.product_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.assertEqual(
            self.dataset_view_1.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        check_affected_dataset_views(
            dataset_id=self.dataset_1.id,
            unique_codes=[self.geographical_entity.unique_code]
        )

        for dataset_view in DatasetView.objects.filter(dataset=self.dataset_1):
            self.assertEqual(
                dataset_view.dataset.sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.product_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.vector_tile_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )

    def test_affect_two_views(self):
        """
        Test Dataset View containing specific entity. Only 2 Dataset
        Views contain this entity.
        """
        self.assertEqual(
            self.dataset_view_1.product_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.assertEqual(
            self.dataset_view_1.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.dataset_view_1.query_string = (
            f'select * from georepo_geographicalentity where '
            f'dataset_id!={self.dataset_1.id}'
        )
        self.dataset_view_1.save()
        create_sql_view(self.dataset_view_1)
        init_view_privacy_level(self.dataset_view_1)
        # init view entity count
        calculate_entity_count_in_view(self.dataset_view_1)
        check_affected_dataset_views(
            dataset_id=self.dataset_1.id,
            entity_id=[self.geographical_entity.id]
        )

        # Dataset View 1 is not affected, since it does not contain the entity.
        # default status if no entity is out of synced
        self.dataset_view_1.refresh_from_db()
        self.assertEqual(
            self.dataset_view_1.product_sync_status,
            DatasetView.SyncStatus.OUT_OF_SYNC
        )
        self.assertEqual(
            self.dataset_view_1.vector_tile_sync_status,
            DatasetView.SyncStatus.OUT_OF_SYNC
        )

        # Other Dataset Views are affected.
        affected_views = DatasetView.objects.exclude(
            id=self.dataset_view_1.id
        ).filter(dataset=self.dataset_1)
        for dataset_view in affected_views:
            self.assertEqual(
                dataset_view.dataset.sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.product_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                dataset_view.vector_tile_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )

    def test_not_affect_static_view(self):
        """
        Test that static Dataset View will not be affected when
        there is entity update.
        """
        static_view = DatasetViewF.create(
            name='custom-1',
            created_by=self.creator,
            dataset=self.dataset_1,
            product_sync_status=DatasetView.SyncStatus.SYNCED,
            vector_tile_sync_status=DatasetView.SyncStatus.SYNCED,
            is_static=True,
            query_string=(
                f'select * from georepo_geographicalentity where '
                f'dataset_id={self.dataset_1.id}'
            )
        )
        create_sql_view(static_view)
        init_view_privacy_level(static_view)
        # init view entity count
        calculate_entity_count_in_view(static_view)
        static_view.product_sync_status = DatasetView.SyncStatus.SYNCED
        static_view.vector_tile_sync_status = DatasetView.SyncStatus.SYNCED
        static_view.save(update_fields=['product_sync_status',
                                        'vector_tile_sync_status'])

        check_affected_dataset_views(
            dataset_id=self.dataset_1.id,
            entity_id=[self.geographical_entity.id]
        )

        # Static View is not affected.
        static_view.refresh_from_db()
        self.assertEqual(
            static_view.product_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.assertEqual(
            static_view.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCED
        )

        # Other views are affected
        affected_views = DatasetView.objects.exclude(
            id=static_view.id
        ).filter(dataset=self.dataset_1)
        for static_view in affected_views:
            self.assertEqual(
                static_view.dataset.sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                static_view.product_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
            self.assertEqual(
                static_view.vector_tile_sync_status,
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
