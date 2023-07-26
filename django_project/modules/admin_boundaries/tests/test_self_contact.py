import fiona
import json
from django.test import override_settings
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.qvector import QVector
from modules.admin_boundaries.geometry_checker.self_contact import (
    self_contact_check
)
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestSelfContact(GeometryCheckTestBase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_contact_point_layer(self):
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
                    self_contact_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_contact_line_layer(self):
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
                    self_contact_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 1)
        error_point = QVector(-1.2280, -0.8654)
        self.assert_check_error(errors, 5, error_point, 0, 0, 0)
        error_point = QVector(-1.2399, -1.0502)
        self.assert_check_error(errors, 5, error_point, 0, 0, 6)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_self_contact_polygon_layer(self):
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
                    self_contact_check(geom, tolerance)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
        self.assertEqual(len(errors), 1)
        error_point = QVector(-0.2080, 1.9830)
        self.assert_check_error(errors, 9, error_point, 0, 0, 3)
