import os
import json
import random
import time

from django.conf import settings
from django.contrib.auth import get_user_model

from core.settings.utils import absolute_path
from georepo.models import (
    Dataset,
    DatasetView, AdminLevelTilingConfig
)

ARCGIS_CONFIG_PATH = absolute_path(
    'georepo', 'utils', 'arcgis_config.json'
)
ARCGIS_BASE_CONFIG_PATH = os.path.join(
    '/', 'home', 'web', 'arcgis'
)


def generate_arcgis_config(
        requester: get_user_model(),
        dataset: Dataset = None,
        dataset_view: DatasetView = None):

    if not dataset and not dataset_view:
        return False

    arcgis_config_file = open(ARCGIS_CONFIG_PATH)
    ctx = json.load(arcgis_config_file)

    if not dataset and dataset_view:
        dataset = dataset_view.dataset

    entity = dataset.geographicalentity_set.filter(
        level=0
    ).first()
    ctx['center'] = ''
    if dataset:
        ctx['id'] = dataset.label.lower().replace(' ', '_')
        ctx['name'] = dataset.label
        vector_tiles = dataset.vector_tiles_path
        if entity:
            ctx['center'] = (
                json.loads(entity.geometry.centroid.json)['coordinates']
            )
        levels = dataset.geographicalentity_set.values_list(
            'level', flat=True).order_by('-level').distinct()
    else:
        vector_tiles = (
            '/layer_tiles/{name}/{{z}}/{{x}}/{{y}}?t={time}'.format(
                name=dataset_view.uuid,
                time=int(time.time())
            )
        )
        ctx['id'] = dataset_view.name.lower().replace(' ', '_')
        ctx['name'] = dataset_view.name
        ctx['bbox'] = dataset_view.bbox.split(',')
        levels = [1]
    layer_tiles_base_url = settings.LAYER_TILES_BASE_URL
    if layer_tiles_base_url[-1] == '/':
        layer_tiles_base_url = layer_tiles_base_url[:-1]
    ctx['sources'] = {
        ctx['name']: {
            'type': 'vector',
            'tiles': [
                f'{layer_tiles_base_url}{vector_tiles}'
                f'&token={str(requester.auth_token)}'
            ],
            'tolerance': 0,
            'minzoom': 1,
            'maxzoom': 8
        }
    }
    ctx['layers'] = []
    for level in levels:
        color = "#" + (
            ''.join([random.choice('0123456789ABCDEF') for j in range(6)])
        )
        if dataset:
            entity_type = dataset.geographicalentity_set.filter(
                level=level
            ).first().type
            layers_config_id = entity_type.label.lower()
            source_layer = f'Level-{level}'
        else:
            source_layer = str(dataset_view.uuid)
            layers_config_id = f'{source_layer}_{dataset_view.id}'
        layers_config = {
            'id': layers_config_id,
            'source': ctx['name'],
            'source-layer': source_layer,
            'type': 'line',
            'paint': {
                'line-color': color,
                'line-width': 1
            }
        }
        if dataset:
            entity_conf = AdminLevelTilingConfig.objects.filter(
                level=level,
                dataset_tiling_config__dataset=dataset
            ).order_by('dataset_tiling_config__zoom_level')
            if entity_conf.exists():
                layers_config['minzoom'] = (
                    entity_conf.first().dataset_tiling_config.zoom_level
                )
                layers_config['maxzoom'] = (
                    entity_conf.last().dataset_tiling_config.zoom_level
                )
        else:
            layers_config['minzoom'] = 1
            layers_config['maxzoom'] = 8

        ctx['layers'].append(layers_config)

    arcgis_config_file.close()

    config_path = f'{ctx["id"]}/VectorTileServer/resources/styles/'
    arcgis_config_full_path = os.path.join(
        ARCGIS_BASE_CONFIG_PATH,
        config_path
    )
    if not os.path.exists(arcgis_config_full_path):
        os.makedirs(arcgis_config_full_path)

    config_file = os.path.join(
        arcgis_config_full_path,
        'root.json'
    )

    if os.path.exists(config_file):
        os.remove(config_file)

    with open(config_file, "w") as outfile:
        json.dump(ctx, outfile, indent=2)

    return True
