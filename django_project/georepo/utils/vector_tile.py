import re
import shutil
import subprocess
import logging
from celery.utils.log import get_task_logger
import toml
import os
import time
from typing import List
from datetime import datetime

from django.conf import settings
from django.db import connection
from django.db.models import Max
from django.db.models.expressions import RawSQL
from celery.result import AsyncResult

from core.settings.utils import absolute_path
from georepo.models import Dataset, DatasetView, \
    EntityId, EntityName, GeographicalEntity, \
    DatasetViewResource
from georepo.utils.dataset_view import create_sql_view, \
    check_view_exists

logger = logging.getLogger(__name__)
celery_logger = get_task_logger(__name__)

TEGOLA_BASE_CONFIG_PATH = os.path.join(
    '/', 'opt', 'tegola_config'
)
TEGOLA_TEMPLATE_CONFIG_PATH = absolute_path(
    'georepo', 'utils', 'config.toml'
)


def dataset_view_sql_query(dataset_view: DatasetView, level,
                           privacy_level, tolerance=None):
    if tolerance:
        select_sql = (
            'SELECT ST_AsMVTGeom(ST_Transform(simplifygeometry(gg.geometry, '
            '{tolerance}), 3857), !BBOX!) AS geometry, '.format(
                tolerance=tolerance
            )
        )
    else:
        select_sql = (
            'SELECT ST_AsMVTGeom('
            'ST_Transform(gg.geometry, 3857), !BBOX!) AS geometry, '
        )
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(dataset_view.uuid))
    # find IdType that the dataset has
    # retrieve all ids in current dataset
    ids = EntityId.objects.filter(
        geographical_entity__dataset__id=dataset_view.dataset.id,
        geographical_entity__level=level,
        geographical_entity__is_approved=True,
        geographical_entity__privacy_level__lte=privacy_level
    )
    ids = ids.filter(
        geographical_entity__id__in=RawSQL(raw_sql, [])
    )
    ids = ids.order_by('code').values(
        'code__id', 'code__name', 'default'
    ).distinct('code__id')
    id_field_left_joins = []
    id_field_select = []
    for id in ids:
        code_id = id['code__id']
        code_name = id['code__name']
        join_name = f'id_{code_id}'
        id_field_select.append(
            f'{join_name}.value as {code_name}'
        )
        id_field_left_joins.append(
            f'LEFT JOIN georepo_entityid {join_name} ON '
            f'{join_name}.geographical_entity_id=gg.id AND '
            f'{join_name}.code_id={code_id}'
        )
    # find Language that the dataset has
    names = EntityName.objects.filter(
        geographical_entity__dataset__id=dataset_view.dataset.id,
        geographical_entity__level=level,
        geographical_entity__is_approved=True,
        geographical_entity__privacy_level__lte=privacy_level
    )
    names = names.filter(
        geographical_entity__id__in=RawSQL(raw_sql, [])
    )
    # get max idx in the names
    names_max_idx = names.aggregate(
        Max('idx')
    )
    name_field_left_joins = []
    name_field_select = []
    if names_max_idx['idx__max'] is not None:
        for name_idx in range(names_max_idx['idx__max'] + 1):
            join_name = f'name_{name_idx+1}'
            name_label = join_name
            name_field_select.append(
                f'{join_name}.name as "{name_label}"'
            )
            name_field_left_joins.append(
                f'LEFT JOIN georepo_entityname {join_name} ON '
                f'{join_name}.geographical_entity_id=gg.id AND '
                f'{join_name}.idx={name_idx} '
            )

    sql = (
        select_sql +
        'ST_AsText(ST_PointOnSurface(gg.geometry)) AS centroid, '
        'gg.id, gg.label, '
        'gg.level, ge.label as type, gg.internal_code as default, '
        'gg.start_date as start_date, gg.end_date as end_date, '
        'pg.label as parent, '
        "pg.unique_code || '_V' || CASE WHEN "
        'pg.unique_code_version IS NULL THEN 1 ELSE '
        'pg.unique_code_version END as parent_ucode, '
        'gg.uuid as concept_uuid, gg.uuid_revision as uuid, '
        'gg.admin_level_name as admin_level_name, '
        "gg.unique_code || '_V' || CASE WHEN "
        'gg.unique_code_version IS NULL THEN 1 ELSE '
        'gg.unique_code_version END as ucode, '
        'gg.unique_code as code ' +
        (', ' if id_field_select else ' ') +
        (', '.join(id_field_select)) + ' ' +
        (', ' if name_field_select else ' ') +
        (', '.join(name_field_select)) + ' '
        'FROM georepo_geographicalentity gg '
        'INNER JOIN georepo_entitytype ge on ge.id = gg.type_id '
        'LEFT JOIN georepo_geographicalentity pg on pg.id = gg.parent_id ' +
        (' '.join(id_field_left_joins)) + ' ' +
        (' '.join(name_field_left_joins)) + ' '
        'WHERE gg.geometry && ST_Transform(!BBOX!, 4326) '
        'AND gg.level = {level} '
        'AND gg.dataset_id = {dataset_id} '
        'AND gg.is_approved=True '
        'AND gg.privacy_level <= {privacy_level} '
        'AND gg.id IN ({raw_sql})'.
        format(
            level=level,
            dataset_id=dataset_view.dataset.id,
            privacy_level=privacy_level,
            raw_sql=raw_sql
        ))
    return sql


class TilingConfigItem(object):

    def __init__(self, level: int, tolerance=None) -> None:
        self.level = level
        self.tolerance = tolerance


class TilingConfigZoomLevels(object):

    def __init__(self, zoom_level: int,
                 items: List[TilingConfigItem]) -> None:
        self.zoom_level = zoom_level
        self.items = items


def get_view_tiling_configs(dataset_view: DatasetView
                            ) -> List[TilingConfigZoomLevels]:
    # return list of tiling configs for dataset_view
    from georepo.models.dataset_tile_config import (
        DatasetTilingConfig
    )
    from georepo.models.dataset_view_tile_config import (
        DatasetViewTilingConfig
    )
    tiling_configs: List[TilingConfigZoomLevels] = []
    view_tiling_conf = DatasetViewTilingConfig.objects.filter(
        dataset_view=dataset_view
    ).order_by('zoom_level')
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
        return tiling_configs
    # check for dataset tiling configs
    dataset_tiling_conf = DatasetTilingConfig.objects.filter(
        dataset=dataset_view.dataset
    ).order_by('zoom_level')
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
        return tiling_configs
    return tiling_configs


def create_view_configuration_files(
        view_resource: DatasetViewResource) -> List[str]:
    """
    Create multiple toml configuration files based on dataset tiling config
    :return: array of output path
    """
    template_config_file = absolute_path(
        'georepo', 'utils', 'config.toml'
    )

    toml_dataset_filepaths = []
    tiling_configs = get_view_tiling_configs(view_resource.dataset_view)
    if len(tiling_configs) == 0:
        return []
    # count levels
    entities = GeographicalEntity.objects.filter(
        dataset=view_resource.dataset_view.dataset,
        is_approved=True,
        privacy_level__lte=view_resource.privacy_level
    )
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(view_resource.dataset_view.uuid))
    entities = entities.filter(
        id__in=RawSQL(raw_sql, [])
    )
    entity_levels = entities.order_by('level').values_list(
        'level',
        flat=True
    ).distinct()
    if len(entity_levels) == 0:
        # means no data for this privacy level
        return []

    for dataset_conf in tiling_configs:
        toml_data = toml.load(template_config_file)
        toml_dataset_filepath = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'view-resource-{view_resource.id}-{dataset_conf.zoom_level}.toml'
        )
        toml_data['maps'] = [{
            'name': f'temp_{str(view_resource.uuid)}',
            'layers': []
        }]
        admin_levels = []
        for adminlevel_conf in dataset_conf.items:
            if adminlevel_conf.level not in entity_levels:
                # skip  if level from tilingconfig is not found in dataset
                continue
            level = adminlevel_conf.level
            if level in admin_levels:
                # skip if level has been added to config
                continue
            sql = dataset_view_sql_query(
                view_resource.dataset_view,
                level,
                view_resource.privacy_level,
                tolerance=adminlevel_conf.tolerance
            )
            provider_layer = {
                'name': f'Level-{level}',
                'geometry_fieldname': 'geometry',
                'id_fieldname': 'id',
                'sql': sql,
                'srid': 3857
            }
            if 'layers' not in toml_data['providers'][0]:
                toml_data['providers'][0]['layers'] = []
            toml_data['providers'][0]['layers'].append(
                provider_layer
            )
            toml_data['maps'][0]['layers'].append({
                'provider_layer': f'docker_postgis.{provider_layer["name"]}'
            })
            admin_levels.append(level)

        toml_dataset_file = open(toml_dataset_filepath, 'w')
        toml_dataset_file.write(
            toml.dumps(toml_data)
        )
        toml_dataset_file.close()
        toml_dataset_filepaths.append({
            'zoom': dataset_conf.zoom_level,
            'config_file': toml_dataset_filepath
        })

    return toml_dataset_filepaths


def generate_view_vector_tiles(view_resource: DatasetViewResource,
                               overwrite: bool = False):
    """
    Generate vector tiles for view
    :param view: DatasetView object
    """
    view_resource.status = DatasetView.DatasetViewStatus.PROCESSING
    view_resource.vector_tiles_progress = 0
    view_resource.save()
    dataset_view_name = str(view_resource.uuid)
    # Create a sql view
    sql_view = str(view_resource.dataset_view.uuid)
    if not check_view_exists(sql_view):
        create_sql_view(view_resource.dataset_view)

    original_vector_tile_path = os.path.join(
        settings.LAYER_TILES_PATH,
        dataset_view_name
    )
    toml_config_files = create_view_configuration_files(view_resource)
    celery_logger.info(
        f'Config files {view_resource.id} - {view_resource.uuid} '
        f'- {len(toml_config_files)}'
    )
    if len(toml_config_files) == 0:
        # no need to generate the view tiles
        if os.path.exists(original_vector_tile_path):
            shutil.rmtree(original_vector_tile_path)
        view_resource.status = DatasetView.DatasetViewStatus.DONE
        view_resource.vector_tiles_progress = 100
        view_resource.save()
        return
    geom_col = 'geometry'

    # Get bbox from sql view
    bbox = []
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT ST_Extent({geom_col}) as bextent FROM "{sql_view}" '
            f'WHERE privacy_level <= {view_resource.privacy_level} AND '
            'is_approved=True'
        )
        extent = cursor.fetchone()
        if extent:
            try:
                bbox = re.findall(r'[-+]?(?:\d*\.\d+|\d+)', extent[0])
            except TypeError:
                pass

    processed_count = 0
    celery_logger.info(
        'Starting vector tile generation for '
        f'view_resource {view_resource.id} - {view_resource.uuid} '
        f'- {view_resource.privacy_level} - overwrite '
        f'- {overwrite}'
    )
    for toml_config_file in toml_config_files:
        command_list = (
            [
                '/opt/tegola',
                'cache',
                'seed',
                '--config',
                toml_config_file['config_file'],
                '--overwrite' if overwrite else '',
                '--concurrency',
                '2',
            ]
        )
        if bbox:
            _bbox = []
            for coord in bbox:
                _bbox.append(str(round(float(coord), 3)))
            view_resource.bbox = ','.join(_bbox)
            command_list.extend([
                '--bounds',
                ','.join(_bbox)
            ])

        if 'zoom' in toml_config_file:
            command_list.extend([
                '--min-zoom',
                str(toml_config_file['zoom']),
                '--max-zoom',
                str(toml_config_file['zoom'])
            ])
        else:
            command_list.extend([
                '--min-zoom',
                '1',
                '--max-zoom',
                '8'
            ])
        result = subprocess.run(command_list, capture_output=True)
        celery_logger.info(
            'Vector tile generation for '
            f'view_resource {view_resource.id} '
            f'- {processed_count} '
            f'finished with exit_code {result.returncode}'
        )
        if result.returncode != 0:
            celery_logger.error(result.stderr)
        processed_count += 1
        view_resource.vector_tiles_progress = (
            (100 * processed_count) / len(toml_config_files)
        )
        celery_logger.info(
            'Processing vector tile generation for '
            f'view_resource {view_resource.id} '
            f'- {view_resource.vector_tiles_progress}'
        )
        view_resource.save()
    celery_logger.info(
        'Finished vector tile generation for '
        f'view_resource {view_resource.id} '
        f'- {view_resource.vector_tiles_progress}'
    )
    if os.path.exists(original_vector_tile_path):
        shutil.rmtree(original_vector_tile_path)

    try:
        shutil.move(
            os.path.join(
                settings.LAYER_TILES_PATH,
                f'temp_{dataset_view_name}'
            ),
            original_vector_tile_path
        )
    except FileNotFoundError:
        view_resource.status = DatasetView.DatasetViewStatus.ERROR
    celery_logger.info(
        'Finished moving temp vector tiles for '
        f'view_resource {view_resource.id} - {view_resource.uuid}'
    )
    view_resource.status = DatasetView.DatasetViewStatus.DONE
    view_resource.vector_tiles_updated_at = datetime.now()
    view_resource.vector_tiles_progress = 100
    view_resource.save()


def check_task_tiling_status(dataset: Dataset) -> str:
    """
    Check tiling status
    Return: status_label
    """
    if dataset.task_id:
        res = AsyncResult(dataset.task_id)
        return dataset.DatasetTilingStatus.DONE if res.ready()\
            else dataset.DatasetTilingStatus.PROCESSING
    return dataset.DatasetTilingStatus.PENDING


def delete_vector_tiles(dataset: Dataset):
    """
    Delete vector tiles directory when dataset is deleted
    """
    vector_tile_path = os.path.join(
        settings.LAYER_TILES_PATH,
        str(dataset.uuid)
    )
    if os.path.exists(vector_tile_path):
        shutil.rmtree(vector_tile_path)


def patch_vector_tile_path():
    """
    Patch vector tile path to use Dataset uuid
    """
    datasets = Dataset.objects.all()
    for dataset in datasets:
        new_vector_dir = str(dataset.uuid)
        if not dataset.vector_tiles_path:
            continue
        if new_vector_dir in dataset.vector_tiles_path:
            continue
        old_vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            dataset.label
        )
        new_vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            new_vector_dir
        )
        try:
            shutil.move(
                old_vector_tile_path,
                new_vector_tile_path
            )
        except FileNotFoundError as ex:
            logger.error('Error renaming vector tiles directory ', ex)
        dataset.vector_tiles_path = (
            f'/layer_tiles/{new_vector_dir}/'
            f'{{z}}/{{x}}/{{y}}?t={int(time.time())}'
        )
        dataset.tiling_status = Dataset.DatasetTilingStatus.DONE
        dataset.save(update_fields=['vector_tiles_path', 'tiling_status'])
        suffix = '.geojson'
        old_geojson_file_path = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            dataset.label
        ) + suffix
        new_geojson_file_path = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(dataset.uuid)
        ) + suffix
        if os.path.exists(old_geojson_file_path):
            try:
                shutil.move(
                    old_geojson_file_path,
                    new_geojson_file_path
                )
            except FileNotFoundError as ex:
                logger.error('Error renaming geojson file ', ex)
