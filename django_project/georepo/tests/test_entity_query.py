from django.test import TestCase
from georepo.utils.entity_query import normalize_attribute_name


class TestProcessGeocodingRequest(TestCase):

    def test_normalize_attribute_name(self):
        name = normalize_attribute_name(
            'name', 0
        )
        self.assertEqual(name, 'name_1')
        name = normalize_attribute_name(
            'adm0_name', 0
        )
        self.assertEqual(name, 'adm0_nam_1')
