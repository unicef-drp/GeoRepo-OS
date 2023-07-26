from typing import List
from django.contrib.gis.geos import (
    GEOSGeometry
)
from .geometry_check_errors import SingleGeometryCheckError
from .geometry_utils import (
    part_count,
    part_at,
    ring_count,
    ring_at,
    vertex_at,
    poly_line_size,
    sqr_distance_2d
)


def duplicate_nodes_check(
        geom: GEOSGeometry,
        tolerance: float) -> List[SingleGeometryCheckError]:
    errors: List[SingleGeometryCheckError] = []
    n_parts = part_count(geom)
    for i_part in range(n_parts):
        geom_part = part_at(geom, i_part)
        n_rings = ring_count(geom_part)
        for i_ring in range(n_rings):
            ring_part = ring_at(geom_part, i_ring)
            n_verts, _ = poly_line_size(ring_part, tolerance)
            if n_verts < 2:
                continue
            i_vert = n_verts - 1
            j_vert = 0
            while j_vert < n_verts:
                pi = vertex_at(ring_part, 0, i_vert)
                pj = vertex_at(ring_part, 0, j_vert)
                if sqr_distance_2d(pi, pj) < tolerance * tolerance:
                    errors.append(
                        SingleGeometryCheckError([pj], i_part,
                                                 i_ring, j_vert)
                    )
                i_vert = j_vert
                j_vert += 1
    return errors
