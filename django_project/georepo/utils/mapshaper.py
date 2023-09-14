import os
import subprocess
import logging
import json
import fiona
import time
from django.db.models import F
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
    ViewAdminLevelTilingConfig
)
from georepo.serializers.entity import SimpleGeographicalGeojsonSerializer
from georepo.utils.custom_geo_functions import ForcePolygonCCW

logger = logging.getLogger(__name__)

SIMPLIFICATION_DOUGLAS_PEUCKER = 'dp'
SIMPLIFICATION_VISVALINGAM = 'visvalingam'
SIMPLIFICATION_VISVALINGAM_WEIGHTED = 'visvalingam_weighted'


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


def export_entities_to_geojson(file_path, queryset):
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


def do_simplify(input_file_path, tolerance):
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
    result = subprocess.run(commands, capture_output=True)
    if result.returncode != 0:
        error = result.stderr.decode()
        logger.error('Failed to simplify with commands')
        logger.error(commands)
        logger.error(error)
        raise RuntimeError(error)
    return output_file.name


def read_output_simplification(output_file_path, tolerance):
    """Read output simplification geojson and insert into Temp table"""
    data = []
    with fiona.open(output_file_path, encoding='utf-8') as collection:
        for feature in collection:
            entity_id = feature['id']
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
                simplified_geometry=geom
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
    # fetch all views with tiling config
    configs = DatasetViewTilingConfig.objects.filter(
        dataset_view__dataset=dataset
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


def copy_entities(dataset: Dataset, level: int):
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=level
    )
    data = []
    for entity in entities.iterator(chunk_size=1):
        data.append(EntitySimplified(
            geographical_entity=entity,
            simplify_tolerance=1,
            simplified_geometry=entity.geometry
        ))
        if len(data) == 5:
            EntitySimplified.objects.bulk_create(data, batch_size=5)
            data.clear()
    if len(data) > 0:
        EntitySimplified.objects.bulk_create(data)


def simplify_for_dataset(dataset: Dataset):
    logger.info(f'Simplification config for dataset {dataset}')
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
    dataset.save(update_fields=['simplification_progress'])
    for level, values in tolerances.items():
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
                dataset.save(
                    update_fields=['simplification_progress']
                )
                logger.info(f'Simplification for dataset {dataset} '
                            f'{progress:.2f}%')
            else:
                export_entities_to_geojson(input_file.name, entities)
                for simplify_factor in values:
                    start = time.time()
                    try:
                        if simplify_factor == 1:
                            copy_entities(dataset, level)
                        else:
                            output_file_path = do_simplify(
                                input_file.name,
                                simplify_factor
                            )
                            read_output_simplification(
                                output_file_path,
                                simplify_factor
                            )
                    except Exception as ex:
                        logger.error(
                            f'Failed to simplify dataset {dataset} '
                            f'level {level} factor {simplify_factor}!'
                        )
                        logger.error(ex)
                    finally:
                        if (
                            output_file_path != input_file.name and
                            os.path.exists(output_file_path)
                        ):
                            os.remove(output_file_path)
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
                        dataset.save(
                            update_fields=['simplification_progress']
                        )
                        logger.info(f'Simplification for dataset {dataset} '
                                    f'{progress:.2f}%')
        except Exception as ex:
            logger.error(f'Failed to simplify dataset {dataset} '
                         f'level {level}!')
            logger.error(ex)
        finally:
            if os.path.exists(input_file.name):
                os.remove(input_file.name)
