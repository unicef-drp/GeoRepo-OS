from core.models.preferences import SitePreferences
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig, AdminLevelTilingConfig
)
from georepo.models.dataset_view_tile_config import (
    DatasetViewTilingConfig, ViewAdminLevelTilingConfig
)


def populate_tile_configs(dataset_id):
    dataset = Dataset.objects.get(id=dataset_id)
    template = SitePreferences.preferences().tile_configs_template
    configs = DatasetTilingConfig.objects.filter(
        dataset=dataset
    )
    configs.delete()
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


def populate_view_tile_configs(view_id):
    dataset_view = DatasetView.objects.get(id=view_id)
    template = SitePreferences.preferences().tile_configs_template
    configs = DatasetViewTilingConfig.objects.filter(
        dataset_view=dataset_view
    )
    configs.delete()
    for config in template:
        tiling_config, _ = DatasetViewTilingConfig.objects.update_or_create(
            dataset_view=dataset_view,
            zoom_level=config['zoom_level']
        )
        ViewAdminLevelTilingConfig.objects.filter(
            view_tiling_config=tiling_config
        ).delete()
        for tile_config in config['tile_configs']:
            ViewAdminLevelTilingConfig.objects.create(
                view_tiling_config=tiling_config,
                level=tile_config['level'],
                simplify_tolerance=tile_config['tolerance']
            )
