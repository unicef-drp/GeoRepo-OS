from django.test import TestCase, override_settings
from georepo.utils import absolute_path
from georepo.utils.gpkg_file import (
    extract_gpkg_attributes,
    get_gpkg_feature_count
)


class TestGpkgFile(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_extract_gpkg_attributes(self):
        gpkg_file_1_path = absolute_path(
            'georepo',
            'tests',
            'gpkg_dataset',
            'gpkg_1_1.gpkg'
        )
        attrs = extract_gpkg_attributes(gpkg_file_1_path)
        self.assertEqual(len(attrs), 7)
        self.assertIn('id', attrs)
        self.assertIn('name_0', attrs)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_get_gpkg_feature_count(self):
        gpkg_file_1_path = absolute_path(
            'georepo',
            'tests',
            'gpkg_dataset',
            'gpkg_1_1.gpkg'
        )
        features_count = get_gpkg_feature_count(gpkg_file_1_path)
        self.assertEqual(features_count, 3)
