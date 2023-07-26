from core.models.preferences import SitePreferences
from georepo.models.dataset import Dataset
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig, AdminLevelTilingConfig
)


def populate_tile_configs(dataset_id):
    dataset = Dataset.objects.get(id=dataset_id)
    template = SitePreferences.preferences().tile_configs_template
    for config in template:
        tiling_config, _ = DatasetTilingConfig.objects.update_or_create(
            dataset=dataset,
            zoom_level=config['zoom_level']
        )
        AdminLevelTilingConfig.objects.filter(
            dataset_tiling_config=tiling_config
        ).delete()
        for tile_config in config['tile_configs']:
            AdminLevelTilingConfig.objects.create(
                dataset_tiling_config=tiling_config,
                level=tile_config['level'],
                simplify_tolerance=tile_config['tolerance']
            )
