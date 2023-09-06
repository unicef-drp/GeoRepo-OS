import json
from django.test import TestCase, override_settings
from georepo.utils import absolute_path
from django.contrib.gis.geos import GEOSGeometry
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF
)
from georepo.utils.geojson import (
    extract_geojson_attributes
)


class TestUtilsGeojson(TestCase):

    def setUp(self) -> None:
        self.entity_type = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_1 = GeographicalEntityF.create(
                revision_number=1,
                level=0,
                dataset=self.dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                label='Pakistan'
            )

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_extract_geojson_attributes(self):
        geojson_file_1_path = absolute_path(
            'georepo',
            'tests',
            'geojson_dataset',
            'level_1.geojson'
        )
        attrs = extract_geojson_attributes(geojson_file_1_path)
        self.assertEqual(len(attrs), 22)
        self.assertIn('code_1', attrs)
        self.assertIn('name_1', attrs)
