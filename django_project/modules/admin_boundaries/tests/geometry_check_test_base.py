from django.test import TestCase
from django.contrib.gis.geos import (
    GEOSGeometry
)


class GeometryCheckTestBase(TestCase):

    def get_geometry(self, feature_idx, geom_str):
        try:
            geom = GEOSGeometry(geom_str)
            return geom
        except Exception as e:
            # TODO: try to make it valid?
            # found below error from polygon:
            # invalid number of points in linearring found 3
            print(f'Failed to load geom at index {feature_idx}')
            print(e)
        return None

    def assert_check_error(self, errors, feature_idx, point,
                           i_part, i_ring, i_vertex=-1, tolerance=1e-4):
        self.assertIn(feature_idx, errors)
        feature_errors = [x for x in errors[feature_idx] if
                          x.part == i_part and x.ring == i_ring and
                          x.vertex == i_vertex]
        self.assertTrue(len(feature_errors) > 0)
        feature_err = feature_errors[0]
        self.assertTrue(len(feature_err.errors) > 0)
        find_point = [x for x in feature_err.errors if
                      x.equals_exact(point, tolerance)]
        self.assertTrue(len(find_point) > 0)
