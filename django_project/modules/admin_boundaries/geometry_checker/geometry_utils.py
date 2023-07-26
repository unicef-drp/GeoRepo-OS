import sys
from typing import List, Tuple
from ctypes import byref, c_double
from django.contrib.gis.geos import prototypes as capi
import math
from django.contrib.gis.geos import (
    GEOSGeometry,
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon
)
from .qvector import QVector

GEOM_COLLECTIONS = (MultiPoint, MultiLineString, MultiPolygon)
DEFAULT_EPSILON = 4 * sys.float_info.epsilon


def vertex_count(geom_part: GEOSGeometry, ring: int) -> int:
    if isinstance(geom_part, Point):
        return 1
    elif isinstance(geom_part, LineString):
        return geom_part.num_coords
    elif isinstance(geom_part, Polygon):
        if ring == 0:
            # get exterior
            return capi.get_num_coords(capi.get_extring(geom_part.ptr))
        return capi.get_num_coords(capi.get_intring(geom_part.ptr, ring - 1))
    return 1


def ring_count(geom_part: GEOSGeometry) -> int:
    if isinstance(geom_part, Point):
        return 1
    elif isinstance(geom_part, LineString):
        return 1 if geom_part.num_coords > 0 else 0
    elif isinstance(geom_part, Polygon):
        return len(geom_part)
    return 1


def part_count(geom: GEOSGeometry) -> int:
    if isinstance(geom, GEOM_COLLECTIONS):
        return geom.num_geom
    return 1 if geom.num_coords > 0 else 0


def part_at(geom: GEOSGeometry, part: int) -> GEOSGeometry:
    if isinstance(geom, GEOM_COLLECTIONS):
        return geom[part]
    return geom


def vertex_at(geom_part: GEOSGeometry, ring: int, vertex: int) -> QVector:
    if isinstance(geom_part, Point):
        return QVector(geom_part.x, geom_part.y)
    elif isinstance(geom_part, LineString):
        return QVector(
            capi.cs_getx(geom_part._cs.ptr, vertex, byref(c_double())),
            capi.cs_gety(geom_part._cs.ptr, vertex, byref(c_double()))
        )
    elif isinstance(geom_part, Polygon):
        if ring == 0:
            p = geom_part.exterior_ring[vertex]
            return QVector(p[0], p[1])
        p = geom_part[ring - 1][vertex]
        return QVector(p[0], p[1])
    return geom_part


def ring_at(geom_part: GEOSGeometry, ring: int) -> GEOSGeometry:
    if isinstance(geom_part, Polygon):
        if ring == 0:
            return geom_part.exterior_ring
        return geom_part[ring - 1]
    return geom_part


def sqr_distance_2d(pt1: QVector, pt2: QVector) -> float:
    return (
        (pt1.x - pt2.x) * (pt1.x - pt2.x) +
        (pt1.y - pt2.y) * (pt1.y - pt2.y)
    )


def project_point_on_segment(p: QVector, s1: QVector, s2: QVector) -> QVector:
    """
    Project the point on a segment
    p The point
    s1 The segment start point
    s2 The segment end point
    returns The projection of the point on the segment
    """
    nx = s2.y - s1.y
    ny = -(s2.x - s1.x)
    t = (
        (p.x * ny - p.y * nx - s1.x * ny + s1.y * nx) /
        ((s2.x - s1.x) * ny - (s2.y - s1.y) * nx)
    )
    return (
        s1 if t < 0. else s2 if t > 1. else
        QVector(s1.x + (s2.x - s1.x) * t, s1.y + (s2.y - s1.y) * t)
    )


def sqr_dist_to_line(ptX: float, ptY: float, x1: float, y1: float,
                     x2: float, y2: float, min_dist_x: float,
                     min_dist_y: float, epsilon: float) -> Tuple[
                         float, float, float]:
    dist = 0
    min_dist_x = x1
    min_dist_y = y1
    dx = x2 - x1
    dy = y2 - y1
    if (
        not math.isclose(dx, 0, abs_tol=DEFAULT_EPSILON) or
        not math.isclose(dy, 0, abs_tol=DEFAULT_EPSILON)
    ):
        t = ((ptX - x1) * dx + (ptY - y1) * dy) / (dx * dx + dy * dy)
        if t > 1:
            min_dist_x = x2
            min_dist_y = y2
        elif t > 0:
            min_dist_x += dx * t
            min_dist_y += dy * t

    dx = ptX - min_dist_x
    dy = ptY - min_dist_y
    dist = dx * dx + dy * dy

    # prevent rounding errors if the point is directly on the segment
    if math.isclose(dist, 0, abs_tol=epsilon):
        min_dist_x = ptX
        min_dist_y = ptY
        return min_dist_x, min_dist_y, 0

    return min_dist_x, min_dist_y, dist


def line_intersection(p1: QVector, v1: QVector, p2: QVector,
                      v2: QVector) -> QVector:
    d = v1.y * v2.x - v1.x * v2.y
    if math.isclose(d, 0, abs_tol=DEFAULT_EPSILON):
        return None

    dx = p2.x - p1.x
    dy = p2.y - p1.y
    k = (dy * v2.x - dx * v2.y) / d

    intersection = QVector(p1.x + v1.x * k, p1.y + v1.y * k)

    # z and m support for intersection point
    # not implemented yet
    # transferFirstZOrMValueToPoint

    return intersection


def segment_intersections(
        p1: QVector, p2: QVector, q1: QVector, q2: QVector,
        tolerance: float,
        accept_improper_intersection: bool = False) -> Tuple[
            bool, bool, QVector]:
    is_intersect = False
    intersection_point: QVector = None
    v = QVector(p2.x - p1.x, p2.y - p1.y)
    w = QVector(q2.x - q1.x, q2.y - q1.y)
    vl = v.length()
    wl = w.length()
    if (
        math.isclose(vl, 0, abs_tol=tolerance) or
        math.isclose(wl, 0, abs_tol=tolerance)
    ):
        return False, is_intersect, intersection_point
    v = v / vl
    w = w / wl
    intersection_point = line_intersection(p1, v, q1, w)
    if intersection_point is None:
        return False, is_intersect, intersection_point
    is_intersect = True
    if accept_improper_intersection:
        if p1 == q1 or p1 == q2:
            return True, is_intersect, p1
        elif p2 == q1 or p2 == q2:
            return True, is_intersect, p2
        x = 0
        y = 0
        # intersectionPoint = p1
        x, y, dist_p1 = sqr_dist_to_line(p1.x, p1.y, q1.x, q1.y, q2.x, q2.y,
                                         x, y, tolerance)
        # intersectionPoint = p2
        x, y, dist_p2 = sqr_dist_to_line(p2.x, p2.y, q1.x, q1.y, q2.x, q2.y,
                                         x, y, tolerance)
        # intersectionPoint = q1
        x, y, dist_q1 = sqr_dist_to_line(q1.x, q1.y, p1.x, p1.y, p2.x, p2.y,
                                         x, y, tolerance)
        # intersectionPoint = q2
        x, y, dist_q2 = sqr_dist_to_line(q2.x, q2.y, p1.x, p1.y, p2.x, p2.y,
                                         x, y, tolerance)
        if (
            math.isclose(dist_p1, 0, abs_tol=tolerance) or
            math.isclose(dist_p2, 0, abs_tol=tolerance) or
            math.isclose(dist_q1, 0, abs_tol=tolerance) or
            math.isclose(dist_q2, 0, abs_tol=tolerance)
        ):
            return True, is_intersect, intersection_point

    lambdav = QVector(intersection_point.x - p1.x,
                      intersection_point.y - p1.y) * v
    if lambdav < tolerance or lambdav > vl - tolerance:
        return False, is_intersect, intersection_point

    lambdaw = QVector(intersection_point.x - q1.x,
                      intersection_point.y - q1.y) * w
    if not (lambdaw < tolerance or lambdaw >= wl - tolerance):
        return True, is_intersect, intersection_point
    return False, is_intersect, intersection_point


class SelfIntersection(object):
    def __init__(self, segment1: int, segment2: int, point: QVector):
        self.segment1 = segment1
        self.segment2 = segment2
        self.point = point


def self_intersections(geom_part: GEOSGeometry, ring: int,
                       tolerance: float) -> List[SelfIntersection]:
    """
    Find self intersections in a polyline
    geom The geometry to check
    part The part of the geometry to check
    ring The ring of the geometry part to check
    tolerance The tolerance to use
    returns The list of self intersections
    """
    intersections = []
    ring_part = ring_at(geom_part, ring)
    n = vertex_count(ring_part, 0)
    is_closed = vertex_at(ring_part, 0, 0) == vertex_at(ring_part, 0, n - 1)
    i = 0
    j = 1
    while j < n:
        pi = vertex_at(ring_part, 0, i)
        pj = vertex_at(ring_part, 0, j)
        if sqr_distance_2d(pi, pj) >= tolerance * tolerance:
            start = j + 1
            end = n - 1 if i == 0 and is_closed else n

            k = start
            m = start + 1
            while m < end:
                pk = vertex_at(ring_part, 0, k)
                pl = vertex_at(ring_part, 0, m)
                is_intersect, _, inter = segment_intersections(pi, pj, pk, pl,
                                                               tolerance)
                if is_intersect:
                    intersection: SelfIntersection
                    if i > k:
                        intersection = SelfIntersection(k, i, inter)
                    else:
                        intersection = SelfIntersection(i, k, inter)
                    intersections.append(intersection)
                k = m
                m += 1

        i = j
        j += 1
    return intersections


def poly_line_size(ring_part: GEOSGeometry,
                   tolerance: float) -> Tuple[int, bool]:
    if not ring_part.empty:
        n_verts = vertex_count(ring_part, 0)
        front = vertex_at(ring_part, 0, 0)
        back = vertex_at(ring_part, 0, n_verts - 1)
        closed = front.equals_exact(back, tolerance)
        return n_verts - 1 if closed else n_verts, closed
    return 0, False
