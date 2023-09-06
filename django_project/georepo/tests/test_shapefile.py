from django.test import TestCase, override_settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile
)
from georepo.utils import absolute_path
from georepo.utils.shapefile import (
    extract_shapefile_attributes,
    get_shape_file_feature_count,
    validate_shapefile_zip
)
from dashboard.tests.model_factories import LayerFileF


class TestShapeFile(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_extract_shapefile_attributes(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_1.zip'
        )
        layer_file = LayerFileF.create(
            layer_file=shape_file_1_path
        )
        attrs = extract_shapefile_attributes(layer_file.layer_file)
        self.assertEqual(len(attrs), 7)
        self.assertIn('id', attrs)
        self.assertIn('name_0', attrs)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_get_shape_file_feature_count(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_1.zip'
        )
        layer_file = LayerFileF.create(
            layer_file=shape_file_1_path
        )
        features_count = get_shape_file_feature_count(layer_file.layer_file)
        self.assertEqual(features_count, 3)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_shapefile_zip(self):
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_1.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_1_path)
        self.assertTrue(is_valid)
        shape_file_2_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_2.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_2_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 2)
        self.assertEqual(error[0], 'test_2.shx')
        self.assertEqual(error[1], 'test_2.dbf')
        shape_file_3_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_3.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_3_path)
        self.assertTrue(is_valid)
        shape_file_4_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_4_no_shp.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_4_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 1)
        self.assertEqual(error[0], 'shp_1_1.shp')
        shape_file_4_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_4_no_dbf.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_4_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 1)
        self.assertEqual(error[0], 'shp_1_1.dbf')
        shape_file_4_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_4_no_shx.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_4_path)
        self.assertFalse(is_valid)
        self.assertEqual(len(error), 1)
        self.assertEqual(error[0], 'shp_1_1.shx')
        # multilayer
        shape_file_5_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_5.zip'
        )
        is_valid, error = validate_shapefile_zip(shape_file_5_path)
        self.assertTrue(is_valid)
        # test from InMemoryUploadedFile
        shape_file_1_path = absolute_path(
            'georepo',
            'tests',
            'shapefile_dataset',
            'shp_1_5.zip'
        )
        with open(shape_file_1_path, 'rb') as file:
            mem_file = InMemoryUploadedFile(file, None, 'shp_1_5.zip',
                                            'application/zip', 1651, None)
            is_valid, error = validate_shapefile_zip(mem_file)
            self.assertTrue(is_valid)
