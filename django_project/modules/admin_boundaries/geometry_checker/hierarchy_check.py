from typing import Tuple, List

from django.contrib.gis.geos import (
    GEOSGeometry
)

from .geometry_check_errors import HierarchyCheckError

# Minimum overlap percentage for HIERARCHY GEOMETRY CHECK
HIERARCHY_OVERLAPS_THRESHOLD = 99


def hierarchy_check(
        geom: GEOSGeometry,
        feature_id: str,
        parent_geom: GEOSGeometry
) -> Tuple[List[HierarchyCheckError], str]:
    errors: List[HierarchyCheckError] = []
    if not geom.valid:
        return errors, geom.valid_reason
    if not parent_geom.valid:
        return errors, parent_geom.valid_reason

    # Check hierarchy by geometry
    if not parent_geom.covers(geom):
        intersection = parent_geom.intersection(
            geom
        )
        overlap_percentage = (
                                 intersection.area / geom.area
                             ) * 100
        if overlap_percentage < HIERARCHY_OVERLAPS_THRESHOLD:
            errors.append(HierarchyCheckError(feature_id, overlap_percentage))

    return errors, None
