import json

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase

from georepo.models import (
    DatasetTilingConfig,
    DatasetViewTilingConfig,
    AdminLevelTilingConfig,
    IdType
)
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF,
    EntityIdF,
    EntityNameF,
    ModuleF
)
from georepo.utils import absolute_path
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest
)
from georepo.utils.dataset_view import (
    init_view_privacy_level
)
from georepo.models.dataset_view import DatasetView
from georepo.models.dataset import Dataset


class TestModelSignal(TestCase):
    """
    Test signals affecting Dataset, DatasetView, and
    DatasetViewResource's sync status
    """

    def setUp(self) -> None:
        self.pCode, _ = IdType.objects.get_or_create(name='PCode')
        self.gid, _ = IdType.objects.get_or_create(name='GID')
        self.entity_type = EntityTypeF.create(label='Country')
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            sync_status=Dataset.SyncStatus.SYNCED
        )
        generate_default_view_dataset_latest(self.dataset)
        self.views_latest = DatasetView.objects.filter(
            dataset=self.dataset
        )
        for view in self.views_latest:
            view.set_synced(True, True, True)
        self.view_latest = self.views_latest.first()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_1 = GeographicalEntityF.create(
                revision_number=1,
                level=0,
                dataset=self.dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                is_approved=True,
                is_latest=True,
                privacy_level=2
            )
            self.entity_id_1 = EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.entity_1,
                default=True,
                value=self.entity_1.internal_code
            )
            EntityIdF.create(
                code=self.gid,
                geographical_entity=self.entity_1,
                default=False,
                value=self.entity_1.id
            )
            self.entity_name_1 = EntityNameF.create(
                geographical_entity=self.entity_1,
                default=True,
                name=self.entity_1.label
            )
        init_view_privacy_level(self.view_latest)
        self.dataset_tconfig_1 = DatasetTilingConfig.objects.create(
            dataset=self.dataset,
            zoom_level=4
        )
        AdminLevelTilingConfig.objects.create(
            dataset_tiling_config=self.dataset_tconfig_1,
            level=self.entity_1.level
        )

    def check_precondition(self):
        # Check precondition: status is synced
        self.assertEqual(
            self.view_latest.product_sync_status,
            DatasetView.SyncStatus.SYNCED
        )
        self.assertEqual(
            self.view_latest.vector_tile_sync_status,
            DatasetView.SyncStatus.SYNCED
        )

    def check_post_condition(self):
        # Check post condition: status is out of sync
        self.dataset.refresh_from_db()
        self.view_latest.refresh_from_db()
        self.assertEqual(
            self.dataset.sync_status,
            Dataset.SyncStatus.OUT_OF_SYNC
        )
        self.assertEqual(
            self.view_latest.product_sync_status,
            DatasetView.SyncStatus.OUT_OF_SYNC
        )
        self.assertEqual(
            self.view_latest.vector_tile_sync_status,
            DatasetView.SyncStatus.OUT_OF_SYNC
        )

    def test_create_entity_id(self):
        """
        Test create entity ID which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Create Entity ID
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=self.entity_1,
            default=True,
            value='some-value'
        )

        self.check_post_condition()

    def test_edit_entity_id(self):
        """
        Test edit entity ID which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Edit Entity ID
        self.entity_id_1.value = 'some-value'
        self.entity_id_1.save()

        self.check_post_condition()

    def test_delete_entity_id(self):
        """
        Test edit entity ID which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Edit Entity ID
        self.entity_id_1.delete()

        self.check_post_condition()

    def test_create_entity_name(self):
        """
        Test create entity name which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Create Entity Name
        EntityNameF.create(
            geographical_entity=self.entity_1,
            default=False,
            name=self.entity_1.label
        )

        self.check_post_condition()

    def test_edit_entity_name(self):
        """
        Test edit entity name which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Edit Entity Name
        self.entity_name_1.name = 'some-value'
        self.entity_id_1.save()

        self.check_post_condition()

    def test_delete_entity_name(self):
        """
        Test edit entity name which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Delete Entity Name
        self.entity_name_1.delete()

        self.check_post_condition()

    def test_edit_entity(self):
        """
        Test edit entity which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Edit Entity source
        self.entity_1.source = 'test'
        self.entity_1.save()

        self.check_post_condition()

    def test_create_entity(self):
        """
        Test edit entity which will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        # Create Entity
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            GeographicalEntityF.create(
                revision_number=1,
                level=0,
                dataset=self.dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='IDN',
                is_approved=True,
                is_latest=True,
                privacy_level=2
            )

        self.check_post_condition()

    def test_dataset_tiling_config_post_create(self):
        """
        Test create Dataset Tiling Config mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        DatasetTilingConfig.objects.create(
            dataset=self.dataset,
            zoom_level=5
        )

        self.check_post_condition()

    def test_dataset_view_tiling_config_post_create(self):
        """
        Test create Dataset View Tiling Config mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        DatasetViewTilingConfig.objects.create(
            dataset_view=self.view_latest,
            zoom_level=5
        )

        self.check_post_condition()

    def test_dataset_view_sql_change(self):
        """
        Test edit Dataset View query string will mark
        Dataset and View as out of sync
        """
        self.check_precondition()

        self.view_latest.query_string = 'select * from geographical_entity'
        self.view_latest.save()

        self.check_post_condition()
