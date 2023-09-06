from django.test import TestCase, override_settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile
)
from georepo.utils import absolute_path
from georepo.utils.layers import \
    validate_layer_file_metadata


class TestShapeFile(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_crs_shapefile_zip(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_3857.zip'
        )
        result, csr, feature_count, attrs = validate_layer_file_metadata(
            shape_file_1_path, 'SHAPEFILE')
        self.assertFalse(result)
        self.assertEqual(feature_count, 3)
        gpkg_file_1_path = absolute_path(
            'georepo',
            'tests',
            'gpkg_dataset',
            'gpkg_1_1.gpkg'
        )
        result, csr, feature_count, attrs = validate_layer_file_metadata(
            gpkg_file_1_path, 'GEOPACKAGE')
        self.assertTrue(result)
        self.assertEqual(feature_count, 3)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_crs_shapefile_zip_memory(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_3857.zip'
        )
        with open(shape_file_1_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(file, None, 'shp_1_3857.zip',
                                            'application/zip', 2586, None)
            result, csr, feature_count, attrs = validate_layer_file_metadata(
                mem_file, 'SHAPEFILE')
            self.assertFalse(result)
            self.assertEqual(feature_count, 3)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_crs_shapefile_zip_gpkg(self):
        gpkg_file_1_path = absolute_path(
            'georepo',
            'tests',
            'gpkg_dataset',
            'gpkg_1_1.gpkg'
        )
        with open(gpkg_file_1_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(file, None, 'gpkg_1_1.gpkg',
                                            'application/geopackage+sqlite3',
                                            106496, None)
            result, csr, feature_count, attrs = validate_layer_file_metadata(
                mem_file, 'GEOPACKAGE')
            self.assertTrue(result)
            self.assertEqual(feature_count, 3)
