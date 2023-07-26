import fiona
import json
from django.test import override_settings
from django.contrib.gis.geos import (
    Point
)
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.duplicate_nodes import (
    duplicate_nodes_check
)
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestDuplicateNodes(GeometryCheckTestBase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_nodes_point_layer(self):
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
                feature_errors = (
                    duplicate_nodes_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_nodes_line_layer(self):
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
                feature_errors = (
                    duplicate_nodes_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 2)
        error_point = Point(-0.6360, 0.6203)
        self.assert_check_error(errors, 0, error_point, 0, 0, 5)
        error_point = Point(0.2473, 2.0821)
        self.assert_check_error(errors, 6, error_point, 0, 0, 1)
        error_point = Point(0.5158, 2.0930)
        self.assert_check_error(errors, 6, error_point, 0, 0, 3)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_nodes_polygon_layer(self):
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
                feature_errors = (
                    duplicate_nodes_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 1)
        error_point = Point(1.6319, 0.5642)
        self.assert_check_error(errors, 4, error_point, 0, 0, 1)
