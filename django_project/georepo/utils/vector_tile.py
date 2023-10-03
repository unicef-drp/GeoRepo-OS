import shutil
import subprocess
import logging
import toml
import os
import time
from typing import List
from datetime import datetime

from django.core.cache import cache
from django.conf import settings
from django.db.models import Max
from django.db.models.expressions import RawSQL
from celery.result import AsyncResult

from core.settings.utils import absolute_path
from georepo.models import Dataset, DatasetView, \
    EntityId, EntityName, GeographicalEntity, \
    DatasetViewResource
from georepo.utils.dataset_view import create_sql_view, \
    check_view_exists, get_entities_count_in_view, generate_view_resource_bbox
from georepo.utils.module_import import module_function
from georepo.utils.azure_blob_storage import (
    DirectoryClient,
    get_tegola_cache_config
)

logger = logging.getLogger(__name__)

TEGOLA_BASE_CONFIG_PATH = os.path.join(
    '/', 'opt', 'tegola_config'
)
TEGOLA_TEMPLATE_CONFIG_PATH = absolute_path(
    'georepo', 'utils', 'config.toml'
)

TEGOLA_AZURE_BASE_PATH = 'layer_tiles'


def dataset_view_sql_query(dataset_view: DatasetView, level,
                           privacy_level,
                           simplify_factor,
                           using_view_tiling_config=False,
                           bbox_param='!BBOX!',
                           intersects_param='ST_Transform(!BBOX!, 4326)',
                           **kwargs):
    """
    Generate sql query for Tegola and Live VT usng ST_AsMVTGeom.

    Note: ST_AsMVTGeom requires the geometry parameter in srid 3857.
    """
    start = time.time()
    select_sql = (
        'SELECT ST_AsMVTGeom('
        'GeomTransformMercator(ges.simplified_geometry), '
        '{bbox_param}) AS geometry, '
    ).format(bbox_param=bbox_param)
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}" where level={}'
    ).format(str(dataset_view.uuid), level)
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
    view_tiling_config_where_cond = ''
    if using_view_tiling_config:
        view_tiling_config_where_cond = (
            f'AND ges.dataset_view_id={dataset_view.id}'
        )
    sql = (
        select_sql +
        'gg.centroid AS centroid, '
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
        'FROM georepo_entitysimplified ges '
        'INNER JOIN georepo_geographicalentity gg on '
        '    gg.id=ges.geographical_entity_id ' +
        'INNER JOIN georepo_entitytype ge on ge.id = gg.type_id '
        'LEFT JOIN georepo_geographicalentity pg on pg.id = gg.parent_id ' +
        (' '.join(id_field_left_joins)) + ' ' +
        (' '.join(name_field_left_joins)) + ' '
        'WHERE ges.simplified_geometry && {intersects_param} '
        'AND ges.simplify_tolerance={simplify_factor} '
        '{view_tiling_config_cond} '
        'AND gg.level={level} '
        'AND gg.dataset_id={dataset_id} '
        'AND gg.is_approved=True '
        'AND gg.privacy_level<={privacy_level} '
        'AND gg.id IN ({raw_sql})'.
        format(
            intersects_param=intersects_param,
            simplify_factor=simplify_factor,
            level=level,
            dataset_id=dataset_view.dataset.id,
            privacy_level=privacy_level,
            raw_sql=raw_sql,
            view_tiling_config_cond=view_tiling_config_where_cond
        ))
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'dataset_view_sql_query',
            end - start)
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


def get_view_tiling_configs(dataset_view: DatasetView, zoom_level: int = None,
                            **kwargs) -> List[TilingConfigZoomLevels]:
    # return list of tiling configs for dataset_view
    from georepo.models.dataset_tile_config import (
        DatasetTilingConfig
    )
    from georepo.models.dataset_view_tile_config import (
        DatasetViewTilingConfig
    )
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


def create_view_configuration_files(
        view_resource: DatasetViewResource, **kwargs) -> List[str]:
    """
    Create multiple toml configuration files based on dataset tiling config
    :return: array of output path
    """
    start = time.time()
    template_config_file = absolute_path(
        'georepo', 'utils', 'config.toml'
    )

    toml_dataset_filepaths = []
    tiling_configs, using_view_tiling_config = get_view_tiling_configs(
        view_resource.dataset_view)
    if len(tiling_configs) == 0:
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'create_view_configuration_files',
                end - start)
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
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'create_view_configuration_files',
                end - start)
        return []

    # get geometry type from module config
    geometry_type = None
    module = view_resource.dataset_view.dataset.module
    if module:
        get_geom_type = module_function(
            module.code_name,
            'config',
            'vector_tile_geometry_type'
        )
        geometry_type = get_geom_type()

    for dataset_conf in tiling_configs:
        toml_data = toml.load(template_config_file)
        toml_dataset_filepath = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'view-resource-{view_resource.id}-{dataset_conf.zoom_level}.toml'
        )
        if settings.USE_AZURE:
            # set the cache to azblobstorage
            toml_data['cache'] = {
                'type': 'azblob',
                'basepath': TEGOLA_AZURE_BASE_PATH
            }
            cache_config = get_tegola_cache_config(
                settings.AZURE_STORAGE, settings.AZURE_STORAGE_CONTAINER)
            toml_data['cache'].update(cache_config)
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
                adminlevel_conf.tolerance,
                using_view_tiling_config=using_view_tiling_config
            )
            provider_layer = {
                'name': f'Level-{level}',
                'geometry_fieldname': 'geometry',
                'id_fieldname': 'id',
                'sql': sql,
                'srid': 3857
            }
            if geometry_type:
                provider_layer['geometry_type'] = geometry_type
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

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'create_view_configuration_files',
            end - start)
    return toml_dataset_filepaths


def generate_view_vector_tiles(view_resource: DatasetViewResource,
                               overwrite: bool = False,
                               **kwargs):
    """
    Generate vector tiles for view
    :param view_resource: DatasetViewResource object
    :param overwrite: True to overwrite existing tiles

    :return boolean: True if vector tiles are generated
    """
    start = time.time()
    view_resource.status = DatasetView.DatasetViewStatus.PROCESSING
    view_resource.vector_tile_sync_status = (
        DatasetViewResource.SyncStatus.SYNCING
    )
    view_resource.vector_tiles_progress = 0
    view_resource.vector_tiles_log = ''
    view_resource.save(update_fields=['status', 'vector_tile_sync_status',
                                      'vector_tiles_progress',
                                      'vector_tiles_log'])
    # Create a sql view
    sql_view = str(view_resource.dataset_view.uuid)
    if not check_view_exists(sql_view):
        create_sql_view(view_resource.dataset_view, **kwargs)
    # check the number of entity in view_resource
    entity_count = get_entities_count_in_view(
        view_resource.dataset_view,
        view_resource.privacy_level,
        **kwargs
    )
    if entity_count == 0:
        logger.info(
            'Skipping vector tiles generation for '
            f'{view_resource.id} - {view_resource.uuid} - '
            f'{view_resource.privacy_level} - Empty Entities'
        )
        remove_vector_tiles_dir(view_resource.resource_id, **kwargs)
        save_view_resource_on_success(view_resource, entity_count)
        calculate_vector_tiles_size(view_resource, **kwargs)
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'generate_view_vector_tiles',
                end - start)
        return False
    else:
        view_resource.entity_count = entity_count
        view_resource.save(update_fields=['entity_count'])

    toml_config_files = create_view_configuration_files(view_resource)
    logger.info(
        f'Config files {view_resource.id} - {view_resource.uuid} '
        f'- {len(toml_config_files)}'
    )
    if len(toml_config_files) == 0:
        # no need to generate the view tiles
        remove_vector_tiles_dir(view_resource.resource_id, **kwargs)
        save_view_resource_on_success(view_resource, entity_count)
        calculate_vector_tiles_size(view_resource, **kwargs)
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'generate_view_vector_tiles',
                end - start)
        return False
    bbox_str = generate_view_resource_bbox(view_resource)

    processed_count = 0
    tegola_concurrency = int(os.getenv('TEGOLA_CONCURRENCY', '2'))
    logger.info(
        'Starting vector tile generation for '
        f'view_resource {view_resource.id} - {view_resource.uuid} '
        f'- {view_resource.privacy_level} - overwrite '
        f'- {overwrite}'
    )
    # generate detail log of vector tile
    detail_logs = {}
    for toml_config_file in toml_config_files:
        current_zoom = toml_config_file['zoom']
        if current_zoom == -1:
            continue
        detail_logs[current_zoom] = {
            'zoom': current_zoom,
            'command_list': '',
            'return_code': -1,
            'time': 0,
            'status': 'pending',
            'error': '',
            'size': 0,
            'total_files': 0,
            'cp_time': 0
        }
    view_resource.vector_tile_detail_logs = detail_logs
    view_resource.save(update_fields=['vector_tile_detail_logs'])
    for toml_config_file in toml_config_files:
        current_zoom = toml_config_file['zoom']
        view_resource.vector_tile_detail_logs[current_zoom]['status'] = (
            'processing'
        )
        view_resource.save(update_fields=[
            'vector_tile_detail_logs'
        ])
        command_list = (
            [
                '/opt/tegola',
                'cache',
                'seed',
                '--config',
                toml_config_file['config_file'],
                '--overwrite' if overwrite else '',
            ]
        )
        if tegola_concurrency > 0:
            command_list.extend([
                '--concurrency',
                f'{tegola_concurrency}',
            ])
        if bbox_str:
            command_list.extend([
                '--bounds',
                bbox_str
            ])

        command_list.extend([
            '--min-zoom',
            str(toml_config_file['zoom']),
            '--max-zoom',
            str(toml_config_file['zoom'])
        ])
        logger.info('Tegola commands:')
        logger.info(command_list)
        subprocess_started = time.time()
        result = subprocess.run(command_list, capture_output=True)
        tegola_time_per_zoom = time.time() - subprocess_started
        logger.info(
            'Vector tile generation for '
            f'view_resource {view_resource.id} '
            f'- {processed_count} '
            f'finished with exit_code {result.returncode}'
        )
        tegola_log_per_zoom = {
            'zoom': current_zoom,
            'command_list': ' '.join(command_list),
            'return_code': result.returncode,
            'time': tegola_time_per_zoom
        }
        if result.returncode != 0:
            logger.error(result.stderr)
            view_resource.status = DatasetView.DatasetViewStatus.ERROR
            view_resource.vector_tiles_log = result.stderr.decode()
            tegola_log_per_zoom['error'] = view_resource.vector_tiles_log
            tegola_log_per_zoom['status'] = 'error'
            view_resource.vector_tile_detail_logs[current_zoom] = (
                tegola_log_per_zoom
            )
            view_resource.save(update_fields=[
                'status', 'vector_tiles_log', 'vector_tile_detail_logs'
            ])
            raise RuntimeError(view_resource.vector_tiles_log)
        tegola_log_per_zoom['status'] = 'copying temp directory'
        dir_size, dir_files = get_current_zoom_level_dir_info(
            view_resource, current_zoom
        )
        tegola_log_per_zoom['size'] = dir_size
        tegola_log_per_zoom['total_files'] = dir_files
        view_resource.vector_tile_detail_logs[current_zoom] = (
            tegola_log_per_zoom
        )
        view_resource.save(update_fields=[
            'vector_tile_detail_logs'
        ])
        cp_started = time.time()
        # do move directory
        on_zoom_level_ends(view_resource, current_zoom)
        cp_time = time.time() - cp_started
        tegola_log_per_zoom['status'] = 'done'
        tegola_log_per_zoom['cp_time'] = cp_time
        view_resource.vector_tile_detail_logs[current_zoom] = (
            tegola_log_per_zoom
        )
        processed_count += 1
        view_resource.vector_tiles_progress = (
            (100 * processed_count) / len(toml_config_files)
        )
        logger.info(
            'Processing vector tile generation for '
            f'view_resource {view_resource.id} '
            f'- {view_resource.vector_tiles_progress}'
        )
        if current_zoom == 0:
            view_resource.vector_tiles_size = dir_size
        else:
            view_resource.vector_tiles_size += dir_size
        view_resource.save(update_fields=[
            'vector_tile_detail_logs',
            'vector_tiles_progress',
            'vector_tiles_size'
        ])
    logger.info(
        'Finished vector tile generation for '
        f'view_resource {view_resource.id} '
        f'- {view_resource.vector_tiles_progress}'
    )

    post_process_vector_tiles(view_resource, toml_config_files, **kwargs)

    logger.info(
        'Finished moving temp vector tiles for '
        f'view_resource {view_resource.id} - {view_resource.uuid}'
    )
    save_view_resource_on_success(view_resource, entity_count)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'generate_view_vector_tiles',
            end - start)
    return True


def save_view_resource_on_success(view_resource, entity_count):
    view_resource.status = (
        DatasetView.DatasetViewStatus.DONE if entity_count > 0 else
        DatasetView.DatasetViewStatus.EMPTY
    )
    view_resource.vector_tile_sync_status = DatasetView.SyncStatus.SYNCED
    view_resource.vector_tiles_updated_at = datetime.now()
    view_resource.vector_tiles_progress = 100
    view_resource.entity_count = entity_count
    view_resource.save(update_fields=['status', 'vector_tile_sync_status',
                                      'vector_tiles_updated_at',
                                      'vector_tiles_progress',
                                      'entity_count'])
    # clear any pending tile cache keys
    reset_pending_tile_cache_keys(view_resource)


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


def remove_vector_tiles_dir(
    resource_id: str,
    is_temp=False,
    **kwargs):
    start = time.time()
    if settings.USE_AZURE:
        client = DirectoryClient(settings.AZURE_STORAGE,
                                 settings.AZURE_STORAGE_CONTAINER)
        layer_tiles_dest = f'layer_tiles/{resource_id}'
        if is_temp:
            layer_tiles_dest = f'layer_tiles/temp_{resource_id}'
        # clear existing directory
        client.rmdir(layer_tiles_dest)
    else:
        original_vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            resource_id
        )
        if is_temp:
            original_vector_tile_path = os.path.join(
                settings.LAYER_TILES_PATH,
                f'temp_{resource_id}'
            )
        if os.path.exists(original_vector_tile_path):
            shutil.rmtree(original_vector_tile_path)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'remove_vector_tiles_dir',
            end - start)


def on_zoom_level_ends(view_resource: DatasetViewResource,
                       current_zoom: int):
    """
    Copy over the current zoom directory to live cache.

    Also remove the zoom from redis to disable live cache VT.
    """
    try:
        if settings.USE_AZURE:
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            layer_tiles_source = (
                f'layer_tiles/temp_{view_resource.resource_id}/{current_zoom}'
            )
            # copy zoom level
            layer_tiles_dest = (
                f'layer_tiles/{view_resource.resource_id}/{current_zoom}'
            )
            directory_to_be_cleared = layer_tiles_dest
            if current_zoom == 0:
                # clear all directories in live cache
                directory_to_be_cleared = (
                    f'layer_tiles/{view_resource.resource_id}'
                )
            client.rmdir(directory_to_be_cleared)
            client.movedir(layer_tiles_source, layer_tiles_dest, is_copy=True)
        else:
            original_vector_tile_path = os.path.join(
                settings.LAYER_TILES_PATH,
                view_resource.resource_id,
                f'{current_zoom}'
            )
            directory_to_be_cleared = original_vector_tile_path
            if current_zoom == 0:
                # clear all directories in live cache
                directory_to_be_cleared = os.path.join(
                    settings.LAYER_TILES_PATH,
                    view_resource.resource_id
                )
            if os.path.exists(directory_to_be_cleared):
                shutil.rmtree(directory_to_be_cleared)
            shutil.copytree(
                os.path.join(
                    settings.LAYER_TILES_PATH,
                    f'temp_{view_resource.resource_id}',
                    f'{current_zoom}'
                ),
                original_vector_tile_path
            )
        if current_zoom == 0:
            # mark other zooms as Pending tile generation
            set_pending_tile_cache_keys(view_resource, True)
        # remove current zoom from cache
        cache_key = (
            f'{view_resource.resource_id}-{current_zoom}-pending-tile'
        )
        cache.delete(cache_key)
    except Exception as ex:
        logger.error(f'Unable to copy zoom {current_zoom} directories ', ex)
        view_resource.status = DatasetView.DatasetViewStatus.ERROR
        view_resource.vector_tiles_log = (
            f'Failed to process Zoom Level {current_zoom} directory'
        )
        view_resource.vector_tile_detail_logs[current_zoom]['status'] = (
            view_resource.vector_tiles_log
        )
        view_resource.save(update_fields=[
            'status', 'vector_tiles_log', 'vector_tile_detail_logs'
        ])
        raise ex


def post_process_vector_tiles(view_resource: DatasetViewResource,
                              toml_config_files,
                              **kwargs):
    try:
        # remove tegola config files
        start = time.time()
        if not settings.DEBUG:
            for toml_config_file in toml_config_files:
                if not os.path.exists(toml_config_file['config_file']):
                    continue
                try:
                    os.remove(toml_config_file['config_file'])
                except Exception as ex:
                    logger.error('Unable to remove config file ', ex)
        if settings.USE_AZURE:
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            layer_tiles_tmp = f'layer_tiles/temp_{view_resource.resource_id}'
            # clear tmp directory
            client.rmdir(layer_tiles_tmp)
        else:
            layer_tiles_tmp = os.path.join(
                settings.LAYER_TILES_PATH,
                f'temp_{view_resource.resource_id}'
            )
            if os.path.exists(layer_tiles_tmp):
                shutil.rmtree(layer_tiles_tmp)
        calculate_vector_tiles_size(view_resource, **kwargs)
        end = time.time()
        if kwargs.get('log_object'):
            kwargs.get('log_object').add_log(
                'post_process_vector_tiles',
                end - start)
    except Exception as ex:
        logger.error('Unable to clear temp directories ', ex)
        view_resource.status = DatasetView.DatasetViewStatus.ERROR
        view_resource.vector_tiles_log = (
            f'Failed to clear temp directories: {str(ex)}'
        )
        view_resource.save(update_fields=['status', 'vector_tiles_log'])
        raise ex


def get_current_zoom_level_dir_info(view_resource: DatasetViewResource,
                                    current_zoom: int):
    """Return directory size and file count."""
    dir_size = 0
    file_count = 0
    try:
        if settings.USE_AZURE:
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            layer_tiles_source = (
                f'layer_tiles/temp_{view_resource.resource_id}/{current_zoom}'
            )
            dir_size, file_count = client.dir_info(layer_tiles_source)
        else:
            original_vector_tile_path = os.path.join(
                settings.LAYER_TILES_PATH,
                f'temp_{view_resource.resource_id}',
                f'{current_zoom}'
            )
            if os.path.exists(original_vector_tile_path):
                for path, dirs, files in os.walk(original_vector_tile_path):
                    for f in files:
                        fp = os.path.join(path, f)
                        dir_size += os.stat(fp).st_size
                        file_count += 1
    except Exception as ex:
        logger.error('Unable to get current zoom directory info ', ex)
    return dir_size, file_count


def calculate_vector_tiles_size(
    view_resource: DatasetViewResource,
    **kwargs):
    start = time.time()
    total_size = 0
    if settings.USE_AZURE:
        client = DirectoryClient(settings.AZURE_STORAGE,
                                 settings.AZURE_STORAGE_CONTAINER)
        layer_tiles_dest = f'layer_tiles/{view_resource.resource_id}'
        total_size = client.dir_size(layer_tiles_dest)
    else:
        original_vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            view_resource.resource_id
        )
        if os.path.exists(original_vector_tile_path):
            for path, dirs, files in os.walk(original_vector_tile_path):
                for f in files:
                    fp = os.path.join(path, f)
                    total_size += os.stat(fp).st_size
    view_resource.vector_tiles_size = total_size
    view_resource.save(update_fields=['vector_tiles_size'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'calculate_vector_tiles_size',
            end - start)


def clean_tegola_config_files(view_resource: DatasetViewResource):
    for zoom in range(21):
        toml_config_file = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'view-resource-{view_resource.id}-{zoom}.toml'
        )
        if not os.path.exists(toml_config_file):
            continue
        try:
            os.remove(toml_config_file)
        except Exception as ex:
            logger.error('Unable to remove config file ', ex)


def reset_pending_tile_cache_keys(view_resource: DatasetViewResource):
    """Reset all pending tile cache from resource."""
    cache_keys = []
    for zoom in range(25):
        cache_keys.append(f'{view_resource.resource_id}-{zoom}-pending-tile')
    cache.delete_many(cache_keys)


def set_pending_tile_cache_keys(
        view_resource: DatasetViewResource,
        skip_zoom_0=False):
    """
    Set pending tile cache based on tiling configs.

    This will be called when:
    - first time generation of vector tiles
    - after zoom level 0 finish generating,
    """
    tiling_configs, is_from_view_config = get_view_tiling_configs(
        view_resource.dataset_view)
    if len(tiling_configs) == 0:
        return 0
    cache_count = 0
    for tiling_config in tiling_configs:
        zoom_level = tiling_config.zoom_level
        if skip_zoom_0 and zoom_level == 0:
            continue
        # for each level in tiling config, generate query
        sqls = {}
        for item in tiling_config.items:
            # check if view resource has entity at this level
            entity_count = get_entities_count_in_view(
                view_resource.dataset_view,
                view_resource.privacy_level,
                item.level
            )
            if entity_count == 0:
                continue
            sqls[item.level] = dataset_view_sql_query(
                view_resource.dataset_view,
                item.level,
                view_resource.privacy_level,
                item.tolerance,
                using_view_tiling_config=is_from_view_config,
                bbox_param='{bbox_param}',
                intersects_param='{intersects_param}'
            )
        cache_key = (
            f'{view_resource.resource_id}-{tiling_config.zoom_level}-'
            'pending-tile'
        )
        cache.set(cache_key, sqls, timeout=None)
        cache_count += 1
    return cache_count
