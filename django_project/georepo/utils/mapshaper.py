import os
import subprocess
import logging
import json
import fiona
from django.db.models import F
from django.db.models.expressions import RawSQL
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from georepo.models import (
    Dataset,
    DatasetView,
    GeographicalEntity,
    EntitySimplified,
    TemporaryEntitySimplified,
    TemporaryTilingConfig
)
from georepo.serializers.entity import GeographicalEntitySerializer
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from georepo.utils.layers import get_feature_value

logger = logging.getLogger(__name__)

SIMPLIFICATION_DOUGLAS_PEUCKER = 'dp'
SIMPLIFICATION_VISVALINGAM = 'visvalingam'
SIMPLIFICATION_VISVALINGAM_WEIGHTED = 'visvalingam_weighted'


class SimpleGeojsonSerializer(
    GeographicalEntitySerializer,
    GeoFeatureModelSerializer):
    remove_empty_fields = False
    output_format = 'geojson'

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'id'
        ]


def mapshaper_commands(input_path: str, output_path: str,
                       simplify: float,
                       simplify_algo: str = SIMPLIFICATION_DOUGLAS_PEUCKER,
                       keep_shapes = True):
    command_list = [
        'mapshaper',
        input_path,
        '-simplify',
        simplify
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
        for entity in queryset.iterator(chunk_size=1):
            data = SimpleGeojsonSerializer(
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


def read_output_for_preview(session, output_file_path, tolerance):
    """Read output simplification geojson and insert into Temp table"""
    with fiona.open(output_file_path, encoding='utf-8') as collection:
        for feature in collection:
            entity_id = get_feature_value(
                feature, 'id'
            )
            # TemporaryEntitySimplified.objects.create(
            #     session=session,
            #     simplify_tolerance=tolerance,
            #     geographical_entity=entity,
            #     simplified_geometry=None
            # )
    if os.path.exists(output_file_path):
        os.remove(output_file_path)


def simplify_for_preview(session, dataset: Dataset, view: DatasetView = None):
    # remove all preview simplified session
    existing = TemporaryEntitySimplified.objects.filter(
        session=session,
        geographical_entity__dataset=dataset
    )
    existing.delete()
    config_levels = TemporaryTilingConfig.objects.filter(
        session=session
    ).order_by('level').values_list(
        'level', flat=True
    ).distinct()
    for config_level in config_levels:
        simplifies = TemporaryTilingConfig.objects.filter(
            session=session,
            level=config_level
        ).order_by('simplify_tolerance').values_list(
            'simplify_tolerance', flat=True
        ).distinct()
        # export entities to geojson file
        input_file = NamedTemporaryFile(
            delete=False,
            suffix='.geojson',
            dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
        )
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=config_level,
            is_approved=True
        )
        if view:
            # raw_sql to view to select id
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(view.uuid))
            # Query existing entities with uuids found in views
            entities = entities.filter(
                id__in=RawSQL(raw_sql, [])
            )
        entities = entities.annotate(
            rhr_geom=AsGeoJSON(ForcePolygonCCW(F('geometry')))
        )
        values = ['id', 'rhr_geom']
        entities = entities.values(*values)
        export_entities_to_geojson(input_file.name, entities)
        for simplify_factor in simplifies:
            output_file_path = do_simplify(input_file.name, simplify_factor)
        if os.path.exists(input_file.name):
            os.remove(input_file.name)

