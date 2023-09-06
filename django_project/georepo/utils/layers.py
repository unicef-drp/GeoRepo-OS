from typing import Tuple
from dashboard.models import (
    LayerFile,
    GEOJSON,
    SHAPEFILE,
    GEOPACKAGE
)
from georepo.utils.geojson import get_geojson_feature_count
from georepo.utils.shapefile import get_shape_file_feature_count
from georepo.utils.gpkg_file import get_gpkg_feature_count


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
