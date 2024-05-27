from typing import List, Tuple
import time
from core.models.preferences import SitePreferences
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig, AdminLevelTilingConfig
)
from georepo.models.dataset_view_tile_config import (
    DatasetViewTilingConfig, ViewAdminLevelTilingConfig
)


class TilingConfigItem(object):

    def __init__(self, level: int, tolerance=None) -> None:
        self.level = level
        self.tolerance = tolerance


class TilingConfigZoomLevels(object):

    def __init__(self, zoom_level: int,
                 items: List[TilingConfigItem]) -> None:
        self.zoom_level = zoom_level
        self.items = items


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


def get_view_tiling_configs(
        dataset_view: DatasetView,
        zoom_level: int = None,
        **kwargs) -> Tuple[List[TilingConfigZoomLevels], bool]:
    """
    Fetch tiling configs for a view.

    When there is no custom tiling config for this view,
    then return tiling config from the dataset.

    :param dataset_view: Dataset View
    :param zoom_level: (Optional) fetch tiling config for this zoom level
    :return: Tuple of (tiling_configs, is_view_tiling_config)
    """
    start = time.time()
    tiling_configs: List[TilingConfigZoomLevels] = []
    view_tiling_conf = DatasetViewTilingConfig.objects.filter(
        dataset_view=dataset_view
    ).order_by('zoom_level')
    if zoom_level is not None:
        view_tiling_conf = view_tiling_conf.filter(
            zoom_level=zoom_level
        )
    if view_tiling_conf.exists():
        for conf in view_tiling_conf:
            items = []
            tiling_levels = conf.viewadminleveltilingconfig_set.all()
            for item in tiling_levels:
                items.append(
                    TilingConfigItem(item.level, item.simplify_tolerance)
                )
            tiling_configs.append(
                TilingConfigZoomLevels(conf.zoom_level, items)
            )
        return tiling_configs, True
    # check for dataset tiling configs
    dataset_tiling_conf = DatasetTilingConfig.objects.filter(
        dataset=dataset_view.dataset
    ).order_by('zoom_level')
    if zoom_level is not None:
        dataset_tiling_conf = dataset_tiling_conf.filter(
            zoom_level=zoom_level
        )
    if dataset_tiling_conf.exists():
        for conf in dataset_tiling_conf:
            items = []
            tiling_levels = conf.adminleveltilingconfig_set.all()
            for item in tiling_levels:
                items.append(
                    TilingConfigItem(item.level, item.simplify_tolerance)
                )
            tiling_configs.append(
                TilingConfigZoomLevels(conf.zoom_level, items)
            )
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'get_view_tiling_configs',
                end - start)
        return tiling_configs, False
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'get_view_tiling_configs',
            end - start)
    return tiling_configs, False


def get_admin_level_tiling_config(
        admin_level: int,
        tiling_configs: List[TilingConfigZoomLevels],
        zoom_level: int) -> Tuple[bool, float]:
    """
    Fetch admin level tolerance from tiling configs.

    :param admin_level: Admin Level
    :param tiling_configs: List of TilingConfigZoomLevels
    :param zoom_level: Zoom level to be checked for
    :return: Tuple of (is_included, tolerance)
    """
    tiling_config_at_zoom = [x for x in tiling_configs if
                             x.zoom_level == zoom_level]
    if len(tiling_config_at_zoom) == 0:
        return False, 0
    tiling_config_at_zoom = tiling_config_at_zoom[0]
    config_item = [x for x in tiling_config_at_zoom.items if
                   x.level == admin_level]
    if len(config_item) == 0:
        return False, 0
    return True, config_item[0].tolerance
