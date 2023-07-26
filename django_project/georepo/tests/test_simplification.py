import json
import mock
from django.test import TestCase
from core.models.preferences import SitePreferences
from georepo.utils import absolute_path
from django.contrib.gis.geos import GEOSGeometry
from georepo.models.entity import EntitySimplified
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF
)
from georepo.utils.tile_configs import populate_tile_configs
from georepo.utils.simplification import process_simplification


def mocked_site_perferences(*args, **kwargs):
    p = SitePreferences()
    p.tile_configs_template = [
        {
            "zoom_level": 0,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 1,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 2,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.0
                },
                {
                    "level": "1",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 3,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0.0
                },
                {
                    "level": "1",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 4,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0.0
                },
                {
                    "level": "2",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 5,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 6,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.0
                },
                {
                    "level": "3",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 7,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0.0
                },
                {
                    "level": "3",
                    "tolerance": 0.0
                }
            ]
        },
        {
            "zoom_level": 8,
            "tile_configs": [
                {
                    "level": "0",
                    "tolerance": 0
                },
                {
                    "level": "1",
                    "tolerance": 0
                },
                {
                    "level": "2",
                    "tolerance": 0
                },
                {
                    "level": "3",
                    "tolerance": 0.0
                },
                {
                    "level": "4",
                    "tolerance": 0.0
                },
                {
                    "level": "5",
                    "tolerance": 0.0
                },
                {
                    "level": "6",
                    "tolerance": 0.0
                }
            ]
        }
    ]
    return p


class TestSimplification(TestCase):

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
                internal_code='PAK'
            )

    @mock.patch('core.models.preferences.SitePreferences.preferences')
    def test_process_simplification(self, perferences):
        perferences.side_effect = mocked_site_perferences
        populate_tile_configs(self.dataset.id)
        process_simplification(self.dataset.id)
        simplified_entities = EntitySimplified.objects.filter(
            geographical_entity=self.entity_1
        ).order_by('simplify_tolerance')
        self.assertEqual(simplified_entities.count(), 1)
        config = simplified_entities[0]
        self.assertEqual(config.simplify_tolerance, 0.0)
