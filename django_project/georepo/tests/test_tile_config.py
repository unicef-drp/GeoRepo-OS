from django.test import TestCase, override_settings
from georepo.utils.tile_configs import populate_tile_configs
from georepo.models.dataset_tile_config import AdminLevelTilingConfig
from georepo.tests.model_factories import DatasetF


class TestPopulateTileConfigs(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_populate_tile_configs(self):
        dataset = DatasetF.create()
        populate_tile_configs(dataset.id)
        tiling_configs = AdminLevelTilingConfig.objects.filter(
            dataset_tiling_config__dataset=dataset
        )
        self.assertNotEqual(tiling_configs.count(), 0)
        tiling_configs_zoom8 = tiling_configs.filter(
            dataset_tiling_config__zoom_level=8
        )
        self.assertTrue(tiling_configs_zoom8.exists())
        self.assertTrue(tiling_configs_zoom8.filter(level=4).exists())
