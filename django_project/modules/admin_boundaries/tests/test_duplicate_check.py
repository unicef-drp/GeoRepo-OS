import fiona
import json
from django.test import override_settings
from georepo.models.entity import GeographicalEntity
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.duplicate_check import (
    duplicate_check
)
from georepo.tests.model_factories import (
    GeographicalEntityF,
    DatasetF
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestDuplicateCheck(GeometryCheckTestBase):

    def init_test_upload(self, layer_file_path):
        dataset = DatasetF.create()
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            layer_file=layer_file_path
        )
        return dataset, layer_file

    def get_duplicate_check_results(self, shape_file_path):
        dataset, layer_file = (
            self.init_test_upload(shape_file_path)
        )
        level = 0
        errors = {}
        geom_errors = {}
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                # queryset for other geom
                other_geoms = GeographicalEntity.objects.filter(
                    dataset=dataset,
                    level=level,
                    layer_file=layer_file
                )
                feature_errors, geom_error = (
                    duplicate_check(geom, str(feature_idx), other_geoms)
                )
                if feature_errors:
                    errors[feature_idx] = feature_errors
                if geom_error:
                    geom_errors[feature_idx] = geom_error
                if not geom_error:
                    # insert to test db if not geom_error
                    GeographicalEntityF.create(
                        dataset=dataset,
                        level=level,
                        geometry=geom,
                        layer_file=layer_file,
                        revision_number=1,
                        internal_code=str(feature_idx),
                        label=str(feature_idx)
                    )
        return errors, geom_errors

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_duplicate_check_point_layer(self):
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'point_layer.zip'
        )
        errors, geom_errors = self.get_duplicate_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(6, errors)
        self.assertEqual(len(errors[6]), 1)
        self.assertEqual(errors[6][0].other_feature_id, '2')
        self.assertEqual(len(geom_errors), 0)

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
        errors, geom_errors = self.get_duplicate_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(7, errors)
        self.assertEqual(len(errors[7]), 1)
        self.assertEqual(errors[7][0].other_feature_id, '4')
        self.assertEqual(len(geom_errors), 0)

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
        errors, geom_errors = self.get_duplicate_check_results(
            shape_file_path
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(8, errors)
        self.assertEqual(len(errors[8]), 1)
        self.assertEqual(errors[8][0].other_feature_id, '7')
        self.assertEqual(len(geom_errors), 2)
