from typing import Tuple, List
from django.db.models import QuerySet
from django.contrib.gis.geos import (
    GEOSGeometry
)
from georepo.models import GeographicalEntity
from .geometry_check_errors import ContainedCheckError


def contained_check(
        geom: GEOSGeometry, feature_id: str,
        other_geom_queryset: QuerySet[GeographicalEntity]) -> Tuple[
            List[ContainedCheckError], str]:
    errors: List[ContainedCheckError] = []
    if not geom.valid:
        return errors, geom.valid_reason
    # find other geometry that has overlaping bbox
    other_geometries = other_geom_queryset.filter(
        geometry__bboverlaps=geom
    )
    for obj in other_geometries:
        if not obj.geometry.valid:
            continue
        # TODO: cannot detect Point on border of polygon
        # If A contains B and B contains A, it would mean that the geometries
        # are identical, which is covered by the duplicate check
        if (
            obj.geometry.contains(geom) and
            not geom.contains(obj.geometry)
        ):
            errors.append(ContainedCheckError(feature_id, obj.internal_code))
    return errors, None
