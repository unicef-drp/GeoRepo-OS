from typing import List
from django.contrib.gis.geos import (
    GEOSGeometry,
    Point
)
from ctypes import POINTER, c_int, c_byte, c_char_p, byref
from django.contrib.gis.geos.libgeos import GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import check_predicate, free
from django.contrib.gis.geos.error import GEOSException
from .geometry_check_errors import SingleGeometryCheckError
from .geometry_utils import (
    self_intersections,
    part_count,
    ring_count,
    part_at
)


def self_intersects_check(
        geom: GEOSGeometry,
        tolerance: float) -> List[SingleGeometryCheckError]:
    n_parts = part_count(geom)
    for i_part in range(n_parts):
        geom_part = part_at(geom, i_part)
        n_rings = ring_count(geom_part)
        for i_ring in range(n_rings):
            intersections = self_intersections(geom_part, i_ring, tolerance)
            if len(intersections) > 0:
                intersection_points = map(lambda x: x.point, intersections)
                return [SingleGeometryCheckError(
                    list(intersection_points),
                    i_part,
                    i_ring
                )]
    return []


def check_valid_detail(result, func, cargs):
    "Error checking for GEOSisValidDetail functions."
    if result == 1:
        # geom is valid
        return True
    elif result == 0:
        return False
    else:
        raise GEOSException(
            'Error encountered on GEOS C '
            'predicate function "%s".' % func.__name__
        )


geos_isvalidreason_with_flag = GEOSFuncFactory(
    "GEOSisValidDetail", restype=c_byte,
    errcheck=check_predicate,
    argtypes=[GEOM_PTR, c_int, POINTER(c_char_p), POINTER(GEOM_PTR)]
)


def self_intersects_check_with_flag(geom: GEOSGeometry):
    # get the reason and free the memory
    reason_ptr = c_char_p()
    # get the location
    out = Point((0, 0))
    is_valid = geos_isvalidreason_with_flag(
        geom.ptr,
        1,
        byref(reason_ptr), byref(out.ptr)
    )
    reason = reason_ptr.value
    free(reason_ptr)
    if not is_valid and b'self-intersection' in reason.lower():
        return False, reason, out
    return True, None, None
