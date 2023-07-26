from typing import Tuple, List
from django.db.models import QuerySet
from django.contrib.gis.geos import (
    GEOSGeometry
)
from georepo.models import GeographicalEntity
from .geometry_check_errors import DuplicateCheckError


def duplicate_check(
        geom: GEOSGeometry, feature_id: str,
        other_geom_queryset: QuerySet[GeographicalEntity]) -> Tuple[
            List[DuplicateCheckError], str]:
    errors: List[DuplicateCheckError] = []
    if not geom.valid:
        return errors, geom.valid_reason
    # find other geometry that has overlaping bbox
    other_geometries = other_geom_queryset.filter(
        geometry__bboverlaps=geom
    )
    for obj in other_geometries:
        if not obj.geometry.valid:
            continue
        if (
            geom.equals(obj.geometry)
        ):
            errors.append(DuplicateCheckError(feature_id, obj.internal_code))
    return errors, None
