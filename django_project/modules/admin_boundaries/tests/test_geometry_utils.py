from django.test import TestCase
from modules.admin_boundaries.geometry_checker.qvector import QVector
from modules.admin_boundaries.geometry_checker.geometry_utils import (
    sqr_dist_to_line,
    segment_intersections
)


class TestGeometryUtils(TestCase):

    def test_sqr_dist_to_line(self):
        qp = QVector(771938, 6.95593e+06)
        p1 = QVector(771946, 6.95593e+06)
        p2 = QVector(771904, 6.95595e+06)
        rx = 0
        ry = 0
        epsilon = 1e-18
        min_dist_x, min_dist_y, dist = sqr_dist_to_line(
            qp.x, qp.y,
            p1.x, p1.y,
            p2.x, p2.y,
            rx, ry,
            epsilon
        )
        self.assertAlmostEqual(dist, 11.83, delta=0.01)

    def test_segment_intersections(self):
        epsilon = 1e-8
        # null
        intersection, is_intersect, inter = segment_intersections(
            QVector(5, 5),
            QVector(5, 5),
            QVector(1, 1),
            QVector(1, 0),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 1),
            QVector(5, 5),
            QVector(5, 5),
            epsilon,
            True
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        # parallel
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 1),
            QVector(1, 1),
            QVector(1, 0),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 1),
            QVector(1, 1),
            QVector(1, 0),
            epsilon,
            True
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(1, 1),
            QVector(0, 1),
            QVector(1, 2),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(5, 5),
            QVector(1, 1),
            QVector(-1, -1),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(5, 5),
            QVector(1, 1),
            QVector(0, 0),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        # contigus
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 5),
            QVector(1, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 5),
            QVector(1, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 5),
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 5),
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            QVector(0, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            QVector(0, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 5),
            QVector(0, 0),
            QVector(1, 5),
            QVector(0, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 5),
            QVector(0, 0),
            QVector(1, 5),
            QVector(0, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 5))
        # colinear
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 5),
            QVector(0, 6),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 5),
            QVector(0, 6),
            epsilon,
            True
        )
        self.assertFalse(intersection)
        self.assertFalse(is_intersect)
        self.assertFalse(inter)
        # improper
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 2),
            QVector(1, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 2),
            QVector(1, 5),
            QVector(0, 0),
            QVector(0, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))

        intersection, is_intersect, inter = segment_intersections(
            QVector(1, 5),
            QVector(0, 2),
            QVector(0, 0),
            QVector(0, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))
        intersection, is_intersect, inter = segment_intersections(
            QVector(1, 5),
            QVector(0, 2),
            QVector(0, 0),
            QVector(0, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))

        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 2),
            QVector(1, 5),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(0, 2),
            QVector(1, 5),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))

        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            QVector(0, 2),
            epsilon
        )
        self.assertFalse(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, 0),
            QVector(0, 5),
            QVector(1, 5),
            QVector(0, 2),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 2))
        # normal
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, -5),
            QVector(0, 5),
            QVector(2, 0),
            QVector(-1, 0),
            epsilon
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 0))
        intersection, is_intersect, inter = segment_intersections(
            QVector(0, -5),
            QVector(0, 5),
            QVector(2, 0),
            QVector(-1, 0),
            epsilon,
            True
        )
        self.assertTrue(intersection)
        self.assertTrue(is_intersect)
        self.assertEqual(inter, QVector(0, 0))
