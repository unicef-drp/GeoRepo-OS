from typing import List
import fiona
import json
import math
from django.test import override_settings
from django.contrib.gis.geos import (
    Point
)
from georepo.models.entity import GeographicalEntity
from georepo.utils import absolute_path
from modules.admin_boundaries.geometry_checker.gap import (
    gap_check
)
from modules.admin_boundaries.geometry_checker.geometry_check_errors import (
    GapCheckError
)
from modules.admin_boundaries.geometry_checker.qrectangle import (
    QRectangle
)
from georepo.tests.model_factories import (
    GeographicalEntityF,
    DatasetF
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from modules.admin_boundaries.tests.geometry_check_test_base import (
    GeometryCheckTestBase
)


class TestGapCheck(GeometryCheckTestBase):

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

    def search_gap_error(self, errors: List[GapCheckError],
                         error_location: Point,
                         gap_area: float, tolerance=1e-4) -> List[
                             GapCheckError]:
        return [x for x in errors if
                math.isclose(x.gap_area, gap_area, abs_tol=tolerance) and
                x.error_location.equals_exact(error_location, tolerance)]

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_gap_check_layer(self):
        tolerance = 1e-8
        gap_threshold_map_units = 0.01
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'gap_layer.zip'
        )
        dataset, layer_file = (
            self.init_test_upload(shape_file_path)
        )
        level = 0
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                # insert to test db for all entities first
                GeographicalEntityF.create(
                    dataset=dataset,
                    level=level,
                    geometry=geom,
                    layer_file=layer_file,
                    revision_number=1,
                    internal_code=str(feature_idx),
                    label=str(feature_idx)
                )
        # run gap check
        geom_queryset = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=level,
            layer_file=layer_file
        )
        gap_errors, check_error = (
            gap_check(geom_queryset, tolerance, gap_threshold_map_units)
        )
        self.assertFalse(check_error)
        self.assertEqual(len(gap_errors), 5)
        # there is different between centroid with test in qgis
        # err_loc = Point(0.4238, -0.7479)
        err_loc = Point(0.41077, -0.74419)
        self.assertEqual(
            len(self.search_gap_error(gap_errors, err_loc, 0.0071)),
            1
        )
        err_loc = Point(0.0094, -0.4448)
        self.assertEqual(
            len(self.search_gap_error(gap_errors, err_loc, 0.0033)),
            1
        )
        err_loc = Point(0.2939, -0.4694)
        self.assertEqual(
            len(self.search_gap_error(gap_errors, err_loc, 0.0053)),
            1
        )
        err_loc = Point(0.6284, -0.3641)
        self.assertEqual(
            len(self.search_gap_error(gap_errors, err_loc, 0.0018)),
            1
        )
        # err_loc = Point(0.2924, -0.8798)
        err_loc = Point(0.2890, -0.8602)
        errs = self.search_gap_error(gap_errors, err_loc, 0.0027)
        self.assertEqual(
            len(errs),
            1
        )
        self.assertTrue(
            errs[0].gap_area_bbox.snapped_to_grid(0.0001) ==
            QRectangle(-0.0259, -1.0198, 0.6178, -0.4481)
        )
        self.assertTrue(
            errs[0].gap_bbox.snapped_to_grid(0.0001) ==
            QRectangle(0.246, -0.9998, 0.3939, -0.77)
        )

    @override_settings(MEDIA_ROOT='/home/web/django_project/modules')
    def test_gap_check_point_in_poly(self):
        tolerance = 1e-8
        gap_threshold_map_units = 0.0
        # read features from zip
        shape_file_path = absolute_path(
            'modules',
            'admin_boundaries',
            'tests',
            'geometry_checker_data',
            'gap_point.zip'
        )
        dataset, layer_file = (
            self.init_test_upload(shape_file_path)
        )
        level = 0
        with fiona.open(f'zip://{shape_file_path}') as features:
            for feature_idx, feature in enumerate(features):
                geom_str = json.dumps(feature['geometry'])
                geom = self.get_geometry(feature_idx, geom_str)
                if not geom:
                    continue
                # insert to test db for all entities first
                GeographicalEntityF.create(
                    dataset=dataset,
                    level=level,
                    geometry=geom,
                    layer_file=layer_file,
                    revision_number=1,
                    internal_code=str(feature_idx),
                    label=str(feature_idx)
                )
        # run gap check
        geom_queryset = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=level,
            layer_file=layer_file
        )
        gap_errors, check_error = (
            gap_check(geom_queryset, tolerance, gap_threshold_map_units)
        )
        self.assertFalse(check_error)
        self.assertEqual(len(gap_errors), 1)
        err = gap_errors[0]
        self.assertTrue(
            err.gap_area_bbox.snapped_to_grid(100) ==
            QRectangle(2.5372e+06, 1.1522e+06, 2.5375e+06, 1.1524e+06)
        )
        self.assertTrue(
            err.gap_bbox.snapped_to_grid(100) ==
            QRectangle(2.5373e+06, 1.1523e+06, 2.5375e+06, 1.1523e+06)
        )
