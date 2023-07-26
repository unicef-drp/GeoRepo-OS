import fiona
import json
from django.test import override_settings
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.valid_nodes import (
    valid_nodes_check
)
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestValidNodesCheck(GeometryCheckTestBase):

    def get_valid_nodes_check_results(self, shape_file_path):
        errors = {}
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom, feature_error = valid_nodes_check(geom_str, feature_idx)
                if feature_error:
                    errors[feature_idx] = feature_error
        return errors

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_valid_nodes_check_point_layer(self):
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'point_layer.zip'
        )
        errors = self.get_valid_nodes_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_check_line_layer(self):
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'line_layer.zip'
        )
        errors = self.get_valid_nodes_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 0)

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_check_polygon_layer(self):
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'polygon_layer.zip'
        )
        errors = self.get_valid_nodes_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(6, errors)
