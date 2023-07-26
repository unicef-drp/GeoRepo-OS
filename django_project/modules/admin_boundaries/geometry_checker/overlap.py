from typing import Tuple, List
from django.db.models import QuerySet
import math
from django.contrib.gis.geos import (
    GEOSGeometry
)
from georepo.models import GeographicalEntity
from .geometry_check_errors import OverlapCheckError
from .geometry_utils import (
    part_count,
    part_at
)


def overlap_check(
        geom: GEOSGeometry,
        other_geom_queryset: QuerySet[GeographicalEntity],
        tolerance: float,
        overlap_threshold_map_units: float,
        reduced_tolerance: float = None) -> Tuple[
            List[OverlapCheckError], str]:
    errors: List[OverlapCheckError] = []
    prep_geom = geom.prepared
    if not geom.valid:
        return errors, geom.valid_reason
    if reduced_tolerance is None:
        # use root square from tolerance
        # this is tolerance for area
        reduced_tolerance = math.sqrt(tolerance)
    # find other geometry that has overlaping bbox
    other_geometries = other_geom_queryset.filter(
        geometry__bboverlaps=geom
    )
    for obj in other_geometries:
        if not prep_geom.overlaps(obj.geometry):
            continue
        inter_geom: GEOSGeometry = geom.intersection(obj.geometry)
        if not inter_geom:
            continue
        n_parts = part_count(inter_geom)
        for i_part in range(n_parts):
            inter_part = part_at(inter_geom, i_part)
            area = inter_part.area
            if (
                area > reduced_tolerance and
                (area < overlap_threshold_map_units or
                 overlap_threshold_map_units == 0.0)
            ):
                errors.append(OverlapCheckError(
                    obj.internal_code, obj.label, inter_part, area
                ))

    return errors, None
