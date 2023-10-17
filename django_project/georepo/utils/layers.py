from typing import Tuple
import time
import json
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.db.models import IntegerField
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


def read_temp_layer_file(upload_session: LayerUploadSession,
                         layer_file: LayerFile):
    """Read layer file and store to EntityTemp table."""
    level = int(layer_file.level)
    # clear existing
    existing_entities = EntityTemp.objects.filter(
        level=level,
        layer_file=layer_file,
        upload_session=upload_session
    )
    existing_entities._raw_delete(existing_entities.db)
    if not layer_file.layer_file.storage.exists(layer_file.layer_file.name):
        return
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
                    if level == 1:
                        ancestor = feature_parent_code
                    else:
                        parent = EntityTemp.objects.filter(
                            upload_session=upload_session,
                            level=level - 1,
                            entity_id=feature_parent_code
                        ).first()
                        if parent:
                            ancestor = parent.ancestor_entity_id
            # add geom
            # create geometry
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
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
                    geometry=geom
                )
            )
            if len(data) == 5:
                EntityTemp.objects.bulk_create(data, batch_size=5)
                data.clear()
        if len(data) > 0:
            EntityTemp.objects.bulk_create(data)
        delete_tmp_shapefile(features.path)


def read_layer_files_entity_temp(upload_session: LayerUploadSession):
    """Read all features from session to EntityTemp."""
    layer_files = LayerFile.objects.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(
        layer_upload_session=upload_session
    ).order_by('level_int')
    for layer_file in layer_files:
        read_temp_layer_file(upload_session, layer_file)
