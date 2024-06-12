import os
import subprocess
import logging
import json
import fiona
import time
import traceback
from django.db.models import F
from django.db.models.expressions import RawSQL
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
from georepo.models import (
    Dataset,
    GeographicalEntity,
    EntitySimplified,
    DatasetTilingConfig,
    AdminLevelTilingConfig,
    DatasetViewTilingConfig,
    ViewAdminLevelTilingConfig,
    DatasetView
)
from georepo.serializers.entity import SimpleGeographicalGeojsonSerializer
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from georepo.utils.directory_helper import convert_size

logger = logging.getLogger(__name__)

SIMPLIFICATION_DOUGLAS_PEUCKER = 'dp'
SIMPLIFICATION_VISVALINGAM = 'visvalingam'
SIMPLIFICATION_VISVALINGAM_WEIGHTED = 'visvalingam_weighted'


def filter_entities_view(view: DatasetView, level: int, entities):
    if level is not None:
        raw_sql = (
            'SELECT id from "{}" where level={}'
        ).format(str(view.uuid), level)
    else:
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(view.uuid))
    return entities.filter(
        id__in=RawSQL(raw_sql, [])
    )


def mapshaper_commands(input_path: str, output_path: str,
                       simplify: float,
                       simplify_algo: str = SIMPLIFICATION_DOUGLAS_PEUCKER,
                       keep_shapes = True):
    command_list = [
        'mapshaper-xl',
        input_path,
        '-simplify',
        str(simplify)
    ]
    if simplify_algo == SIMPLIFICATION_DOUGLAS_PEUCKER:
        command_list.append('dp')
    elif simplify_algo == SIMPLIFICATION_VISVALINGAM:
        command_list.append('visvalingam')
    elif simplify_algo == SIMPLIFICATION_VISVALINGAM_WEIGHTED:
        command_list.extend([
            'visvalingam',
            'weighted'
        ])
    if keep_shapes:
        command_list.append('keep-shapes')
    command_list.extend([
        '-o',
        output_path
    ])
    return command_list


def export_entities_to_geojson(file_path, queryset, level):
    with open(file_path, "w") as geojson_file:
        geojson_file.write('{\n')
        geojson_file.write('"type": "FeatureCollection",\n')
        geojson_file.write('"features": [\n')
        idx = 0
        total_count = queryset.count()
        for entity in queryset.iterator(chunk_size=2):
            data = SimpleGeographicalGeojsonSerializer(
                entity,
                many=False
            ).data
            data['geometry'] = '{geom_placeholder}'
            feature_str = json.dumps(data)
            feature_str = feature_str.replace(
                '"{geom_placeholder}"',
                entity['rhr_geom']
            )
            geojson_file.write(feature_str)
            if idx == total_count - 1:
                geojson_file.write('\n')
            else:
                geojson_file.write(',\n')
            idx += 1
        geojson_file.write(']\n')
        geojson_file.write('}\n')
    file_size = os.path.getsize(file_path)
    logger.info(f'Entities level {level} are exported '
                f'to {file_path} with size {convert_size(file_size)}')


def export_entities_to_geojson_with_neighbors(file_path, dataset,
                                              entity_id, view=None):
    with open(file_path, "w") as geojson_file:
        geojson_file.write('{\n')
        geojson_file.write('"type": "FeatureCollection",\n')
        geojson_file.write('"features": [\n')
        idx = 0
        single_entity = GeographicalEntity.objects.filter(
            id=entity_id
        ).annotate(
            rhr_geom=AsGeoJSON(
                ForcePolygonCCW(F('geometry')),
                precision=6
            )
        ).values('id', 'rhr_geom', 'level', 'geometry')[0]
        data = SimpleGeographicalGeojsonSerializer(
            single_entity,
            many=False
        ).data
        data['geometry'] = '{geom_placeholder}'
        feature_str = json.dumps(data)
        feature_str = feature_str.replace(
            '"{geom_placeholder}"',
            single_entity['rhr_geom']
        )
        geojson_file.write(feature_str)

        # query other entities
        other_entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=single_entity['level']
        )
        if view:
            other_entities = filter_entities_view(
                view, single_entity['level'], other_entities)
        other_entities = other_entities.filter(
            geometry__touches=single_entity['geometry']
        ).exclude(
            id=entity_id
        ).annotate(
            rhr_geom=AsGeoJSON(
                ForcePolygonCCW(F('geometry')),
                precision=6
            )
        ).values('id', 'rhr_geom')
        total_count = other_entities.count()
        if total_count > 0:
            geojson_file.write(',\n')
        else:
            geojson_file.write('\n')

        for entity in other_entities.iterator(chunk_size=2):
            data = SimpleGeographicalGeojsonSerializer(
                entity,
                many=False
            ).data
            data['geometry'] = '{geom_placeholder}'
            feature_str = json.dumps(data)
            feature_str = feature_str.replace(
                '"{geom_placeholder}"',
                entity['rhr_geom']
            )
            geojson_file.write(feature_str)
            if idx == total_count - 1:
                geojson_file.write('\n')
            else:
                geojson_file.write(',\n')
            idx += 1
        geojson_file.write(']\n')
        geojson_file.write('}\n')


def do_simplify(input_file_path, tolerance, level, show_log=True):
    if tolerance == 1:
        return input_file_path
    output_file = NamedTemporaryFile(
        delete=False,
        suffix='.geojson',
        dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
    )
    commands = mapshaper_commands(
        input_file_path,
        output_file.name,
        tolerance
    )
    if show_log:
        logger.info('Mapshaper commands:')
        logger.info(commands)
    result = subprocess.run(commands, capture_output=True)
    output = result.stdout.decode()
    if show_log:
        logger.info(output)
    if result.returncode != 0:
        error = result.stderr.decode()
        logger.error('Failed to simplify with commands')
        logger.error(commands)
        logger.error(error)
        raise RuntimeError(error)
    if show_log:
        file_size = os.path.getsize(output_file.name)
        logger.info(f'Entities level {level} are simplified '
                    f'to {output_file.name} with size '
                    f'{convert_size(file_size)}')
    return output_file.name


def read_output_simplification(output_file_path, tolerance,
                               view=None, input_ids=None):
    """Read output simplification geojson and insert into Temp table"""
    data = []
    with fiona.open(output_file_path, encoding='utf-8') as collection:
        for feature in collection:
            entity_id = int(feature['id'])
            if input_ids is not None and entity_id not in input_ids:
                continue
            entity = GeographicalEntity.objects.filter(
                id=entity_id
            ).first()
            if entity is None:
                continue
            geom_str = json.dumps(feature['geometry'])
            geom = None
            try:
                geom = GEOSGeometry(geom_str)
            except Exception:
                pass
            if geom is None:
                continue
            elif isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            data.append(EntitySimplified(
                geographical_entity=entity,
                simplify_tolerance=tolerance,
                simplified_geometry=geom,
                dataset_view=view
            ))
            if len(data) == 5:
                EntitySimplified.objects.bulk_create(data, batch_size=5)
                data.clear()
        if len(data) > 0:
            EntitySimplified.objects.bulk_create(data)


def get_dataset_simplification(dataset: Dataset):
    tolerances = {}
    # fetch datasettiling configs
    configs = DatasetTilingConfig.objects.filter(
        dataset=dataset
    )
    for config in configs:
        tiling_configs = AdminLevelTilingConfig.objects.filter(
            dataset_tiling_config=config
        )
        for tiling_config in tiling_configs:
            if tiling_config.level not in tolerances:
                tolerances[tiling_config.level] = []
            if (
                tiling_config.simplify_tolerance not in
                tolerances[tiling_config.level]
            ):
                tolerances[tiling_config.level].append(
                    tiling_config.simplify_tolerance)
    return tolerances


def get_dataset_view_tolerance(view: DatasetView):
    tolerances = {}
    # fetch all views with tiling config
    configs = DatasetViewTilingConfig.objects.filter(
        dataset_view=view
    )
    for config in configs:
        tiling_configs = ViewAdminLevelTilingConfig.objects.filter(
            view_tiling_config=config
        )
        for tiling_config in tiling_configs:
            if tiling_config.level not in tolerances:
                tolerances[tiling_config.level] = []
            if (
                tiling_config.simplify_tolerance not in
                tolerances[tiling_config.level]
            ):
                tolerances[tiling_config.level].append(
                    tiling_config.simplify_tolerance)
    return tolerances


def copy_entities(dataset: Dataset, level: int, view: DatasetView = None):
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=level
    )
    if view:
        entities = filter_entities_view(view, level, entities)
    data = []
    for entity in entities.iterator(chunk_size=1):
        data.append(EntitySimplified(
            geographical_entity=entity,
            simplify_tolerance=1,
            simplified_geometry=entity.geometry,
            dataset_view=view
        ))
        if len(data) == 5:
            EntitySimplified.objects.bulk_create(data, batch_size=5)
            data.clear()
    if len(data) > 0:
        EntitySimplified.objects.bulk_create(data)


def on_simplify_for_dataset_started(dataset: Dataset):
    logger.info(f'Simplification config for dataset {dataset}')
    dataset.simplification_progress = (
        'Entity simplification starts'
    )
    dataset.simplification_progress_num = 0
    dataset.simplification_sync_status = Dataset.SyncStatus.SYNCING
    dataset.save(update_fields=['simplification_progress',
                                'simplification_sync_status',
                                'simplification_progress_num'])
    logger.info(dataset.simplification_progress)


def on_simplify_for_dataset_finished(dataset: Dataset, is_success: bool):
    if is_success:
        # success
        dataset.simplification_progress = (
            'Entity simplification finished'
        )
        dataset.is_simplified = True
        dataset.simplification_sync_status = Dataset.SyncStatus.SYNCED
        dataset.save(update_fields=[
            'simplification_progress', 'is_simplified',
            'simplification_sync_status'])
        logger.info(dataset.simplification_progress)
    else:
        # error
        logger.error('Dataset simplification got error '
                     f'at {dataset.simplification_progress}')
        dataset.simplification_progress = (
            'Entity simplification error '
            f'at {dataset.simplification_progress}'
        )
        dataset.is_simplified = False
        dataset.simplification_sync_status = Dataset.SyncStatus.ERROR
        dataset.save(update_fields=[
            'simplification_progress', 'is_simplified',
            'simplification_sync_status'])


def simplify_for_dataset(
    dataset: Dataset,
    **kwargs
):
    start = time.time()
    on_simplify_for_dataset_started(dataset)
    tolerances = get_dataset_simplification(dataset)
    logger.info(tolerances)
    total_simplification = 0
    for level, values in tolerances.items():
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=level
        )
        if not entities.exists():
            continue
        total_simplification += len(values)
    processed_count = 0
    dataset.simplification_progress = '0%'
    dataset.simplification_progress_num = 0
    dataset.save(update_fields=['simplification_progress',
                                'simplification_progress_num'])
    for level, values in tolerances.items():
        input_file = None
        try:
            # clear all existing simplified entities
            existing_entities = EntitySimplified.objects.filter(
                geographical_entity__dataset=dataset,
                geographical_entity__level=level
            )
            existing_entities._raw_delete(existing_entities.db)
            entities = GeographicalEntity.objects.filter(
                dataset=dataset,
                level=level
            )
            entities = entities.annotate(
                rhr_geom=AsGeoJSON(
                    ForcePolygonCCW(F('geometry')),
                    precision=6
                )
            )
            entities = entities.values('id', 'rhr_geom')
            if entities.count() == 0:
                continue
            logger.info(f'Simplification for dataset {dataset} level {level} '
                        f'total entities: {entities.count()}')
            # export entities to geojson file
            input_file = NamedTemporaryFile(
                delete=False,
                suffix='.geojson',
                dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
            )
            if len(values) == 1 and values[0] == 1:
                # skip simplification and just copy over the entities
                copy_entities(dataset, level)
                processed_count += 1
                progress = (
                    (100 * processed_count) / total_simplification
                )
                dataset.simplification_progress = f'{progress:.2f}%'
                dataset.simplification_progress_num = progress
                dataset.save(
                    update_fields=['simplification_progress',
                                   'simplification_progress_num']
                )
                logger.info(f'Simplification for dataset {dataset} '
                            f'{progress:.2f}%')
            else:
                export_entities_to_geojson(input_file.name, entities, level)
                for simplify_factor in values:
                    start = time.time()
                    output_file_path = ''
                    try:
                        if simplify_factor == 1:
                            copy_entities(dataset, level)
                        else:
                            output_file_path = do_simplify(
                                input_file.name,
                                simplify_factor,
                                level
                            )
                            read_output_simplification(
                                output_file_path,
                                simplify_factor
                            )
                        end = time.time()
                        logger.info(f'Simplification for dataset {dataset} '
                                    f'level {level} simplify '
                                    f'{simplify_factor} '
                                    f'finished: {end-start}s')
                        processed_count += 1
                        progress = (
                            (100 * processed_count) / total_simplification
                        )
                        dataset.simplification_progress = f'{progress:.2f}%'
                        dataset.simplification_progress_num = progress
                        dataset.save(
                            update_fields=['simplification_progress',
                                           'simplification_progress_num']
                        )
                        logger.info(f'Simplification for dataset {dataset} '
                                    f'{progress:.2f}%')
                    except Exception as ex:
                        logger.error(
                            f'Failed to simplify dataset {dataset} '
                            f'level {level} factor {simplify_factor}!'
                        )
                        logger.error(ex)
                        logger.error(traceback.format_exc())
                        raise ex
                    finally:
                        if (
                            output_file_path != input_file.name and
                            os.path.exists(output_file_path)
                        ):
                            os.remove(output_file_path)
        except Exception:
            logger.error(f'Failed to simplify dataset {dataset} '
                         f'level {level}!')
        finally:
            if input_file and os.path.exists(input_file.name):
                os.remove(input_file.name)
    is_simplify_success = processed_count == total_simplification
    on_simplify_for_dataset_finished(dataset, is_simplify_success)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('simplify_for_dataset', end - start)
    return is_simplify_success


def simplify_for_dataset_view(
    view: DatasetView,
    **kwargs
):
    start = time.time()
    tolerances = get_dataset_view_tolerance(view)
    logger.info(f'Simplification config for view {view}')
    logger.info(tolerances)
    if len(tolerances.keys()) == 0:
        view.simplification_progress = (
            f'Entity simplification finished for {view}'
        )
        view.simplification_progress_num = 100
        view.simplification_sync_status = DatasetView.SyncStatus.SYNCED
        view.save(update_fields=['simplification_progress',
                                 'simplification_sync_status',
                                 'simplification_progress_num'])
        return True
    view.simplification_progress = (
        'Entity simplification starts'
    )
    view.simplification_progress_num = 0
    view.simplification_sync_status = DatasetView.SyncStatus.SYNCING
    view.save(update_fields=['simplification_progress',
                             'simplification_sync_status',
                             'simplification_progress_num'])
    logger.info(view.simplification_progress)
    total_simplification = 0
    for level, values in tolerances.items():
        entities = GeographicalEntity.objects.filter(
            dataset=view.dataset,
            level=level
        )
        entities = filter_entities_view(view, level, entities)
        if not entities.exists():
            continue
        total_simplification += len(values)
    processed_count = 0
    view.simplification_progress = '0%'
    view.simplification_progress_num = 0
    view.save(update_fields=['simplification_progress',
                             'simplification_progress_num'])
    for level, values in tolerances.items():
        input_file = None
        try:
            # clear all existing simplified entities
            existing_entities = EntitySimplified.objects.filter(
                geographical_entity__level=level,
                dataset_view=view
            )
            existing_entities._raw_delete(existing_entities.db)
            entities = GeographicalEntity.objects.filter(
                dataset=view.dataset,
                level=level
            )
            entities = filter_entities_view(view, level, entities)
            entities = entities.annotate(
                rhr_geom=AsGeoJSON(
                    ForcePolygonCCW(F('geometry')),
                    precision=6
                )
            )
            entities = entities.values('id', 'rhr_geom')
            if entities.count() == 0:
                continue
            logger.info(f'Simplification for view {view} level {level} '
                        f'total entities: {entities.count()}')
            # export entities to geojson file
            input_file = NamedTemporaryFile(
                delete=False,
                suffix='.geojson',
                dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
            )
            if len(values) == 1 and values[0] == 1:
                # skip simplification and just copy over the entities
                copy_entities(view.dataset, level, view)
                processed_count += 1
                progress = (
                    (100 * processed_count) / total_simplification
                )
                view.simplification_progress = f'{progress:.2f}%'
                view.simplification_progress_num = progress
                view.save(
                    update_fields=['simplification_progress',
                                   'simplification_progress_num']
                )
                logger.info(f'Simplification for view {view} '
                            f'{progress:.2f}%')
            else:
                export_entities_to_geojson(input_file.name, entities, level)
                for simplify_factor in values:
                    start = time.time()
                    output_file_path = ''
                    try:
                        if simplify_factor == 1:
                            copy_entities(view.dataset, level, view)
                        else:
                            output_file_path = do_simplify(
                                input_file.name,
                                simplify_factor,
                                level
                            )
                            read_output_simplification(
                                output_file_path,
                                simplify_factor,
                                view
                            )
                        end = time.time()
                        logger.info(f'Simplification for view {view} '
                                    f'level {level} simplify '
                                    f'{simplify_factor} '
                                    f'finished: {end-start}s')
                        processed_count += 1
                        progress = (
                            (100 * processed_count) / total_simplification
                        )
                        view.simplification_progress = f'{progress:.2f}%'
                        view.simplification_progress_num = progress
                        view.save(
                            update_fields=['simplification_progress',
                                           'simplification_progress_num']
                        )
                        logger.info(f'Simplification for view {view} '
                                    f'{progress:.2f}%')
                    except Exception as ex:
                        logger.error(
                            f'Failed to simplify view {view} '
                            f'level {level} at factor {simplify_factor}!'
                        )
                        logger.error(ex)
                        logger.error(traceback.format_exc())
                        raise ex
                    finally:
                        if (
                            output_file_path != input_file.name and
                            os.path.exists(output_file_path)
                        ):
                            os.remove(output_file_path)
        except Exception:
            logger.error(f'Failed to simplify view {view} '
                         f'level {level}!')
        finally:
            if input_file and os.path.exists(input_file.name):
                os.remove(input_file.name)
    if processed_count == total_simplification:
        # success
        view.simplification_progress = (
            'Entity simplification finished'
        )
        view.simplification_sync_status = DatasetView.SyncStatus.SYNCED
        view.save(update_fields=['simplification_progress',
                                 'simplification_sync_status'])
        logger.info(view.simplification_progress)
    else:
        # error
        logger.error('Dataset simplification for view got error '
                     f'at {view.simplification_progress}')
        view.simplification_progress = (
            'Entity simplification error '
            f'at {view.simplification_progress}'
        )
        view.simplification_sync_status = DatasetView.SyncStatus.ERROR
        view.save(update_fields=['simplification_progress',
                                 'simplification_sync_status'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'simplify_for_dataset_view',
            end - start
        )
    return processed_count == total_simplification


def simplify_for_dataset_low_memory(dataset: Dataset, **kwargs):
    start = time.time()
    on_simplify_for_dataset_started(dataset)
    tolerances = get_dataset_simplification(dataset)
    logger.info(tolerances)
    dataset.simplification_progress = '0%'
    dataset.simplification_progress_num = 0
    dataset.save(update_fields=['simplification_progress',
                                'simplification_progress_num'])
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level__in=list(tolerances.keys())
    ).values('id', 'level', 'internal_code').order_by('id')
    total_entities = entities.count()
    processed_count = 0
    for entity in entities:
        entity_id = entity['id']
        level = entity['level']
        code = entity['internal_code']
        input_file = None
        output_file_path = None
        try:
            # clear existing entities
            existing_entities = EntitySimplified.objects.filter(
                geographical_entity_id=entity_id
            )
            existing_entities._raw_delete(existing_entities.db)
            tolerance_values = tolerances[level]
            if len(tolerance_values) == 0:
                processed_count += 1
                continue
            # export entities to geojson file
            input_file = NamedTemporaryFile(
                delete=False,
                suffix='.geojson',
                dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
            )
            # do export here
            export_entities_to_geojson_with_neighbors(
                input_file.name, dataset, entity_id)
            for simplify_factor in tolerance_values:
                if simplify_factor == 1:
                    entity_with_geom = GeographicalEntity.objects.get(
                        id=entity_id
                    )
                    EntitySimplified.objects.create(
                        geographical_entity=entity_with_geom,
                        simplify_tolerance=1,
                        simplified_geometry=entity_with_geom.geometry
                    )
                else:
                    output_file_path = do_simplify(
                        input_file.name, simplify_factor, level, False
                    )
                    read_output_simplification(
                        output_file_path, simplify_factor,
                        input_ids=[entity_id]
                    )
                    if output_file_path and os.path.exists(output_file_path):
                        os.remove(output_file_path)
            processed_count += 1
        except Exception as ex:
            logger.error(f'Failed to simplify dataset {dataset} - '
                         f'entity {entity_id} - {code}!')
            logger.error(ex)
            logger.error(traceback.format_exc())
        finally:
            if input_file and os.path.exists(input_file.name):
                os.remove(input_file.name)
            if output_file_path and os.path.exists(output_file_path):
                os.remove(output_file_path)
    is_simplify_success = processed_count == total_entities
    on_simplify_for_dataset_finished(dataset, is_simplify_success)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('simplify_for_dataset', end - start)
    return is_simplify_success
