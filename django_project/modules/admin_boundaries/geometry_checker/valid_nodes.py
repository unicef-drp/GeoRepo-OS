from typing import Tuple
from django.contrib.gis.geos import (
    GEOSGeometry
)
from .geometry_check_errors import InvalidGeometryNodesError


def valid_nodes_check(geom_str: str,
                      feature_id: str) -> Tuple[GEOSGeometry,
                                                InvalidGeometryNodesError]:
    geom = None
    error = None
    try:
        geom = GEOSGeometry(geom_str)
    except Exception as ex:
        error = InvalidGeometryNodesError(feature_id, str(ex))
    return (geom, error)
