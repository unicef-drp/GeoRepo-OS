import json

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase

from core.settings.utils import absolute_path
from georepo.tests.model_factories import (
    DatasetF
)
from modules.admin_boundaries.geometry_checker.hierarchy_check import (
    hierarchy_check
)


class TestHierarchyCheck(TestCase):

    def setUp(self):
        self.dataset = DatasetF.create()
        self.geojson_0 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_0.geojson')
        with open(self.geojson_0) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geom_0 = GEOSGeometry(geom_str)
        self.geojson_1 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_1.geojson')
        with open(self.geojson_1) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geom_1 = GEOSGeometry(geom_str)

    def test_hierarchy_check_valid(self):
        result = hierarchy_check(
            self.geom_1, 'internal-code', self.geom_0
        )
        self.assertEqual(
            result,
            ([], None)
        )

    def test_hierarchy_check_invalid(self):
        result = hierarchy_check(
            self.geom_0, 'internal-code', self.geom_1
        )
        self.assertEqual(len(result[0]), 1)
