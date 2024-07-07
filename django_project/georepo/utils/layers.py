from typing import Tuple
import time
import json
import logging
import traceback
import csv
from io import StringIO
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.db.models import IntegerField
from django.core.files.base import ContentFile
from django.db.models.functions import Cast
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
import fiona
from fiona.crs import from_epsg
from fiona.io import (
    MemoryFile
)
from dashboard.models import (
    LayerFile,
    GEOJSON,
    SHAPEFILE,
    GEOPACKAGE,
    LayerUploadSession,
    EntityTemp
)
from georepo.utils.geojson import get_geojson_feature_count
from georepo.utils.shapefile import get_shape_file_feature_count
from georepo.utils.gpkg_file import get_gpkg_feature_count
from georepo.utils.fiona_utils import (
    open_collection,
    delete_tmp_shapefile,
    store_zip_memory_to_temp_file,
    open_collection_by_file
)


logger = logging.getLogger(__name__)


def get_attributes(collection):
    attrs = []
    try:
        attrs = next(iter(collection))["properties"].keys()
    except (KeyError, IndexError):
        pass
    return list(attrs)


def check_properties(
        layer_file: LayerFile
) -> Tuple[list | None, int]:
    error_messages = []
    feature_count = 0

    if not layer_file:
        return error_messages, feature_count
    if layer_file.layer_type == GEOJSON:
        feature_count = get_geojson_feature_count(
            layer_file.layer_file
        )
    elif layer_file.layer_type == SHAPEFILE:
        feature_count = get_shape_file_feature_count(
            layer_file.layer_file
        )
    elif layer_file.layer_type == GEOPACKAGE:
        feature_count = get_gpkg_feature_count(
            layer_file.layer_file
        )

    return error_messages, feature_count


def check_valid_value(feature: any, field_name: str) -> bool:
    """
    Validate if feature value is valid:
    - field_name exists in feature properties
    - value is not null and not empty string
    """
    value = get_feature_value(feature, field_name)
    return str(value).strip() != ''


def get_feature_value(feature, field_name, default='') -> str:
    """
    Read properties value from field_name from single feature
    """
    value = (
        feature['properties'][field_name] if
        field_name in feature['properties'] else None
    )
    if value is None:
        # None is possible if read from shape file
        value = default
    else:
        # convert the returned value as string
        value = str(value).strip()
    return value


def get_crs_epsg(crs):
    return crs['init'] if 'init' in crs else None


def validate_layer_file_metadata(layer_file_obj: any, type: any):
    """Validate crs to be EPSG:4326"""
    start = time.time()
    epsg_mapping = from_epsg(4326)
    valid = False
    crs = None
    feature_count = 0
    attributes = []
    # if less than <2MB, it will be InMemoryUploadedFile
    if isinstance(layer_file_obj, InMemoryUploadedFile):
        if type == 'SHAPEFILE':
            # fiona having issues with reading ZipMemoryFile
            # need to store to temp file
            tmp_file = store_zip_memory_to_temp_file(layer_file_obj)
            with fiona.open(tmp_file) as collection:
                valid = get_crs_epsg(collection.crs) == epsg_mapping['init']
                crs = get_crs_epsg(collection.crs)
                feature_count = len(collection)
                attributes = get_attributes(collection)
            delete_tmp_shapefile(collection.path, False)
        else:
            # geojson/geopackage can be read using MemoryFile
            with MemoryFile(layer_file_obj.file) as file:
                with file.open() as collection:
                    valid = (
                        get_crs_epsg(collection.crs) == epsg_mapping['init']
                    )
                    crs = get_crs_epsg(collection.crs)
                    feature_count = len(collection)
                    attributes = get_attributes(collection)
    else:
        # TemporaryUploadedFile or just string to file path
        file_path = layer_file_obj
        if isinstance(layer_file_obj, TemporaryUploadedFile):
            file_path = (
                f'zip://{layer_file_obj.temporary_file_path()}' if
                type == 'SHAPEFILE' else
                f'{layer_file_obj.temporary_file_path()}'
            )
            with fiona.open(file_path) as collection:
                valid = (
                    get_crs_epsg(collection.crs) == epsg_mapping['init']
                )
                crs = get_crs_epsg(collection.crs)
                feature_count = len(collection)
                attributes = get_attributes(collection)
        else:
            with open_collection(file_path, type) as collection:
                valid = (
                    get_crs_epsg(collection.crs) == epsg_mapping['init']
                )
                crs = get_crs_epsg(collection.crs)
                feature_count = len(collection)
                attributes = get_attributes(collection)
    end = time.time()
    print(f'validate_layer_file_metadata {(end - start)}')
    return valid, crs, feature_count, attributes


def fetch_layer_file_metadata(layer_file: LayerFile):
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as collection:
        layer_file.feature_count = len(collection)
        layer_file.attributes = get_attributes(collection)
        layer_file.save(update_fields=['feature_count', 'attributes'])
        delete_tmp_shapefile(collection.path)


def build_geom_object(geom_str: str):
    geom = None
    try:
        geom = GEOSGeometry(geom_str)
    except Exception:
        logger.error('Error building geom object ', geom)
    return geom


def read_temp_layer_file(upload_session: LayerUploadSession,
                         layer_file: LayerFile):
    """Read layer file and store to EntityTemp table."""
    level = int(layer_file.level)
    validation_result = {
        'level': level,
        'parent_code_missing': [],
        'parent_missing': []
    }
    # clear existing
    existing_entities = EntityTemp.objects.filter(
        level=level,
        layer_file=layer_file,
        upload_session=upload_session
    )
    existing_entities._raw_delete(existing_entities.db)
    if not layer_file.layer_file.storage.exists(layer_file.layer_file.name):
        return validation_result
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    name_field = (
        [name_field['field'] for name_field in layer_file.name_fields
            if name_field['default']][0]
    )
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as features:
        data = []
        for feature_idx, feature in enumerate(features):
            # default code
            entity_id = get_feature_value(
                feature, id_field
            )
            # default name
            entity_name = get_feature_value(
                feature, name_field
            )
            # parent code
            feature_parent_code = None
            # find ancestor
            ancestor = None
            if level > 0:
                feature_parent_code = (
                    get_feature_value(
                        feature, layer_file.parent_id_field
                    )
                )
                if feature_parent_code:
                    parent = EntityTemp.objects.filter(
                        upload_session=upload_session,
                        level=level - 1,
                        entity_id=feature_parent_code
                    ).first()
                    if level == 1:
                        ancestor = feature_parent_code
                    elif parent:
                        ancestor = parent.ancestor_entity_id
                    if parent is None and level > 1:
                        # parent missing
                        validation_result['parent_missing'].append({
                            'level': level,
                            'feature_id': feature_idx,
                            'name': entity_name,
                            'entity_id': entity_id,
                            'parent': feature_parent_code
                        })
                elif level > 1:
                    # parent code missing error
                    validation_result['parent_code_missing'].append({
                        'level': level,
                        'feature_id': feature_idx,
                        'name': entity_name,
                        'entity_id': entity_id,
                        'parent': None
                    })
            # add geom
            # create geometry
            geom_str = json.dumps(feature['geometry'])
            geom = build_geom_object(geom_str)
            if geom and isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            # add metadata
            location_type_value = None
            if layer_file.location_type_field:
                location_type_value = (
                    get_feature_value(feature, layer_file.location_type_field)
                )
            source_value = None
            if layer_file.source_field:
                source_value = (
                    get_feature_value(feature, layer_file.source_field)
                )
            privacy_level_value = None
            if layer_file.privacy_level_field:
                privacy_level_value = (
                    get_feature_value(feature, layer_file.privacy_level_field)
                )
            boundary_type_value = None
            if layer_file.boundary_type:
                boundary_type_value = (
                    get_feature_value(feature, layer_file.boundary_type)
                )
            id_fields = []
            for id_field_data in layer_file.id_fields:
                id_fields.append({
                    'field': id_field_data['field'],
                    'value': get_feature_value(
                        feature, id_field_data['field']),
                    'idType': id_field_data['idType'],
                    'default': id_field_data['default']
                })
            name_fields = []
            for name_field_data in layer_file.name_fields:
                name_fields.append({
                    'field': name_field_data['field'],
                    'value': get_feature_value(
                        feature, name_field_data['field']),
                    'default': name_field_data['default'],
                    'label': (
                        name_field_data['label'] if 'label' in
                        name_field_data else ''
                    ),
                    'selectedLanguage': name_field_data['selectedLanguage']
                })
            metadata = {
                'entity_type': layer_file.entity_type,
                'location_type_field': layer_file.location_type_field,
                'location_type_value': location_type_value,
                'parent_id_field': layer_file.parent_id_field,
                'parent_id_value': feature_parent_code,
                'source_field': layer_file.source_field,
                'source_value': source_value,
                'privacy_level': layer_file.privacy_level,
                'privacy_level_field': layer_file.privacy_level_field,
                'privacy_level_value': privacy_level_value,
                'id_fields': id_fields,
                'name_fields': name_fields,
                'boundary_type': layer_file.boundary_type,
                'boundary_type_value': boundary_type_value
            }
            data.append(
                EntityTemp(
                    level=level,
                    layer_file=layer_file,
                    upload_session=upload_session,
                    feature_index=feature_idx,
                    entity_name=entity_name,
                    entity_id=entity_id,
                    parent_entity_id=feature_parent_code,
                    ancestor_entity_id=ancestor,
                    geometry=geom,
                    metadata=metadata
                )
            )
            if len(data) == 5:
                EntityTemp.objects.bulk_create(data, batch_size=5)
                data.clear()
        if len(data) > 0:
            EntityTemp.objects.bulk_create(data)
        delete_tmp_shapefile(features.path)
        return validation_result


def read_layer_files_entity_temp(upload_session: LayerUploadSession):
    """Read all features from session to EntityTemp."""
    layer_files = LayerFile.objects.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(
        layer_upload_session=upload_session
    ).order_by('level_int')
    for layer_file in layer_files:
        validation_result = read_temp_layer_file(upload_session, layer_file)
        if validation_result['level'] > 1:
            # save into upload session
            upload_session.validation_summaries[validation_result['level']] = (
                validation_result
            )
            upload_session.save(update_fields=['validation_summaries'])
    # write validation_summaries into csv file
    store_validation_summaries(upload_session)


def check_value_as_string_valid(value: str):
    """Validate if it is not empty string."""
    if value is None:
        return False
    return str(value).strip() != ''


def check_tmp_entity_metadata_valid(metadata, field):
    """Validate if field value is not empty."""
    if field not in metadata:
        return False
    value = metadata[field] if metadata[field] else ''
    return check_value_as_string_valid(value)


def store_validation_summaries(upload_session: LayerUploadSession):
    """Store validation summaries into csv file."""
    rows = []
    for summary in upload_session.validation_summaries.values():
        if len(summary) == 0:
            continue
        rows.extend(summary)
    if len(rows) == 0:
        upload_session.validation_report = None
        upload_session.save(update_fields=['validation_report'])
        return
    try:
        keys = rows[0].keys()
        csv_buffer = StringIO()
        csv_writer = csv.DictWriter(csv_buffer, keys)
        csv_writer.writeheader()
        csv_writer.writerows(rows)

        csv_file = ContentFile(csv_buffer.getvalue().encode('utf-8'))
        upload_session.validation_report.save(
            f'validation-summaries-{upload_session.id}.csv',
            csv_file
        )
    except Exception as e:
        logger.error(
            'There is unexpected error in store_validation_summaries')
        logger.error(e)
        logger.error(traceback.format_exc())
