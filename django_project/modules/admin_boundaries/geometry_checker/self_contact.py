from typing import List
from django.contrib.gis.geos import (
    GEOSGeometry
)
from .geometry_check_errors import SingleGeometryCheckError
from .qvector import QVector
from .geometry_utils import (
    part_count,
    ring_count,
    vertex_at,
    vertex_count,
    sqr_distance_2d,
    project_point_on_segment,
    part_at,
    ring_at
)


def self_contact_check(
        geom: GEOSGeometry,
        tolerance: float) -> List[SingleGeometryCheckError]:
    errors: List[SingleGeometryCheckError] = []
    n_parts = part_count(geom)
    square_tolerance = tolerance * tolerance
    for i_part in range(n_parts):
        geom_part = part_at(geom, i_part)
        n_rings = ring_count(geom_part)
        for i_ring in range(n_rings):
            # Test for self-contacts
            ring_part = ring_at(geom_part, i_ring)
            n = vertex_count(ring_part, 0)
            is_closed = vertex_at(ring_part, 0, 0).equals_exact(
                vertex_at(ring_part, 0, n - 1), tolerance)

            # Geometry ring without duplicate nodes
            vtx_map: List[int] = []
            ring: List[QVector] = []
            vtx_map.append(0)
            ring.append(vertex_at(ring_part, 0, 0))
            i = 1
            while i < n:
                p = vertex_at(ring_part, 0, i)
                if sqr_distance_2d(p, ring[-1]) > square_tolerance:
                    vtx_map.append(i)
                    ring.append(p)
                i += 1
            while (
                len(ring) > 0 and
                sqr_distance_2d(ring[0], ring[-1]) < square_tolerance
            ):
                vtx_map.pop()
                ring.pop()
            if len(ring) > 0 and is_closed:
                vtx_map.append(n - 1)
                ring.append(ring[0])
            n = len(ring)

            # For each vertex, check whether it lies on a segment
            i_vert = 0
            n_verts = n - 1 if is_closed else n
            while i_vert < n_verts:
                p = ring[i_vert]
                i = 0
                j = 1
                while j < n:
                    if (
                        i_vert == i or i_vert == j or
                        (is_closed and i_vert == 0 and j == n - 1)
                    ):
                        i = j
                        j += 1
                        continue
                    si = ring[i]
                    sj = ring[j]
                    q = project_point_on_segment(p, si, sj)
                    if sqr_distance_2d(p, q) < square_tolerance:
                        errors.append(
                            SingleGeometryCheckError([p], i_part,
                                                     i_ring, vtx_map[i_vert])
                        )
                        # No need to report same contact on
                        # ifferent segments multiple times
                        break

                    i = j
                    j += 1
                i_vert += 1
    return errors
