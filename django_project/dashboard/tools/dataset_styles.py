import json
from datetime import datetime
from georepo.models.boundary_type import BoundaryType
from georepo.utils import absolute_path
from django.urls import reverse
from django.conf import settings
from core.models.preferences import SitePreferences
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig
)
from georepo.models.dataset_view_tile_config import (
    DatasetViewTilingConfig
)


DEFAULT_STYLE_PATH = absolute_path(
    'dashboard', 'tools', 'default_style.json'
)
HIGHLIGHT_COLOR = '#32cd32'
VECTOR_LINE_COLORS = [
    '#FF69B4',
    '#37f009',
    '#096FF0',
    '#d9f009',
    '#fa02cd',
    '#fa5d02'
]


def get_dashboard_tiles_url(
        request, dataset, session=None,
        revised_entity=None, level=None,
        revision=None, boundary_type=None,
        dataset_view_uuid=None):
    url = ''
    if revised_entity and level:
        url = (
            reverse('dashboard-tiles-review', kwargs={
                'dataset': str(dataset.uuid),
                'level': level,
                'revised_entity': revised_entity,
                'z': 0,
                'x': 0,
                'y': 0
            })
        )
    elif revision and boundary_type:
        # replace boundary_type value with label of EntityType
        obj = BoundaryType.objects.filter(
            value=boundary_type,
            dataset=dataset
        ).first()
        if obj:
            boundary_type = obj.type.label
        url = (
            reverse('dashboard-tiles-review-boundary-lines', kwargs={
                'dataset': str(dataset.uuid),
                'revision': revision,
                'boundary_type': boundary_type,
                'z': 0,
                'x': 0,
                'y': 0
            })
        )
    elif dataset_view_uuid and session:
        url = (
            reverse('dashboard-tiles-view', kwargs={
                'dataset_view': str(dataset_view_uuid),
                'session': session,
                'z': 0,
                'x': 0,
                'y': 0
            })
        )
    else:
        url = (
            reverse('dashboard-tiles', kwargs={
                'session': (
                    session if session else 'dataset_' + str(dataset.uuid)
                ),
                'z': 0,
                'x': 0,
                'y': 0
            })
        )
    epoch = datetime.now().strftime('%s')
    url = request.build_absolute_uri(url)
    url = url.replace('/0/0/0', '/{z}/{x}/{y}') + f'?dt={epoch}'
    if not settings.DEBUG:
        # if not dev env, then replace with https
        url = url.replace('http://', 'https://')
    return url


def replace_source_tile_url(
        request, styles, source_name,
        dataset, session=None,
        revised_entity=None, level=None,
        revision=None, boundary_type=None,
        dataset_view_uuid=None):
    """ replace tiles url with server base url + session if any """
    if 'sources' not in styles:
        return styles
    sources = styles['sources']
    if source_name not in sources:
        return styles
    style = sources[source_name]
    url = get_dashboard_tiles_url(
        request, dataset, session, revised_entity, level,
        revision, boundary_type, dataset_view_uuid
    )
    style['tiles'] = [url]
    return styles


def find_max_zoom(dataset, dataset_view_uuid=None):
    zoom_level = -1
    if dataset_view_uuid:
        view_tiling_conf = DatasetViewTilingConfig.objects.filter(
            dataset_view__uuid=dataset_view_uuid
        ).order_by('-zoom_level').first()
        if view_tiling_conf:
            zoom_level = view_tiling_conf.zoom_level
    if zoom_level == -1:
        dataset_tiling_conf = DatasetTilingConfig.objects.filter(
            dataset=dataset
        ).order_by('-zoom_level').first()
        if dataset_tiling_conf:
            zoom_level = dataset_tiling_conf.zoom_level
    return zoom_level if zoom_level != -1 else 8


def generate_default_style(
        request, dataset, session=None,
        revised_entity=None, level=None,
        revision=None, boundary_type=None,
        dataset_view_uuid=None):
    """ generate default style dataset """
    styles = {}
    with open(DEFAULT_STYLE_PATH) as config_file:
        styles = json.load(config_file)
    source_name = (
        dataset.style_source_name if
        dataset.style_source_name else str(dataset.uuid)
    )
    url = get_dashboard_tiles_url(
        request, dataset, session, revised_entity, level,
        revision, boundary_type, dataset_view_uuid
    )
    # maxzoom uses from tiling configs
    source = {
        'type': 'vector',
        'tiles': [url],
        'tolerance': 0,
        'maxzoom': find_max_zoom(dataset, dataset_view_uuid),
        'minzoom': 0
    }
    styles['sources'][source_name] = source
    entities = dataset.geographicalentity_set.all().order_by('-level')
    levels = entities.values_list('level', flat=True).distinct()
    for level in levels:
        layer_id = f'level_{level}'
        layer = {
            'id': layer_id,
            'source': source_name,
            'source-layer': layer_id,
            'type': 'line',
            'paint': {
                'line-color': [
                    'case',
                    ['boolean', ['feature-state', 'hover'], False],
                    HIGHLIGHT_COLOR,
                    VECTOR_LINE_COLORS[level % len(VECTOR_LINE_COLORS)]
                ],
                'line-width': [
                    'case',
                    ['boolean', ['feature-state', 'hover'], False],
                    4,
                    1
                ]
            }
        }
        styles['layers'].append(layer)
    return styles


def replace_maptiler_api_key(styles):
    map_tiler_key = SitePreferences.preferences().maptiler_api_key
    if 'glyphs' in styles and styles['glyphs']:
        styles['glyphs'] = styles['glyphs'].replace(
            '{{maptiler_key}}',
            map_tiler_key
        )
    if 'sources' in styles and 'openmaptiles' in styles['sources']:
        if 'url' in styles['sources']['openmaptiles']:
            styles['sources']['openmaptiles']['url'] = (
                styles['sources']['openmaptiles']['url'].replace(
                    '{{maptiler_key}}',
                    map_tiler_key
                )
            )
    return styles
