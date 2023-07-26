import fiona
import json
from django.test import override_settings
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.qvector import QVector
from modules.admin_boundaries.geometry_checker.self_intersects import (
    self_intersects_check
)
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestSelfIntersects(GeometryCheckTestBase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_intersects_point_layer(self):
        tolerance = 1e-8
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'point_layer.zip'
        )
        errors = {}
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                intersect_errors = (
                    self_intersects_check(geom, tolerance)
                )
                if intersect_errors:
                    errors[feature_idx] = intersect_errors
        self.assertEqual(len(errors), 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_intersects_line_layer(self):
        tolerance = 1e-8
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'line_layer.zip'
        )
        errors = {}
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                intersect_errors = (
                    self_intersects_check(geom, tolerance)
                )
                if intersect_errors:
                    errors[feature_idx] = intersect_errors
        self.assertEqual(len(errors), 2)
        intersect1_point = QVector(-0.1997, 0.1044)
        self.assert_check_error(errors, 1, intersect1_point, 0, 0)
        intersect8_point = QVector(-1.1985, 0.3128)
        self.assert_check_error(errors, 8, intersect8_point, 0, 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_intersects_polygon_layer(self):
        tolerance = 1e-8
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'polygon_layer.zip'
        )
        errors = {}
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                intersect_errors = (
                    self_intersects_check(geom, tolerance)
                )
                if intersect_errors:
                    errors[feature_idx] = intersect_errors
        self.assertEqual(len(errors), 2)
        intersect1_point = QVector(1.2592, 0.0888)
        self.assert_check_error(errors, 1, intersect1_point, 0, 0)
        intersect12_point = QVector(0.2213, 0.2365)
        self.assert_check_error(errors, 12, intersect12_point, 0, 0)
