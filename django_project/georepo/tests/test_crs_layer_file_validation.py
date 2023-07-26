from django.test import TestCase, override_settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile
)
from georepo.utils import absolute_path
from georepo.utils.crs_layer_file_validation import \
    validate_layer_file_in_crs_4326


class TestShapeFile(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_crs_shapefile_zip(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_3857.zip'
        )
        result, csr = validate_layer_file_in_crs_4326(
            shape_file_1_path, 'SHAPEFILE')
        self.assertFalse(result)
        gpkg_file_1_path = absolute_path(
            'georepo',
            'tests',
            'gpkg_dataset',
            'gpkg_1_1.gpkg'
        )
        result, csr = validate_layer_file_in_crs_4326(
            gpkg_file_1_path, 'GEOPACKAGE')
        self.assertTrue(result)

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
            result, csr = validate_layer_file_in_crs_4326(
                mem_file, 'SHAPEFILE')
            self.assertFalse(result)

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
            result, csr = validate_layer_file_in_crs_4326(
                mem_file, 'GEOPACKAGE')
            self.assertTrue(result)
