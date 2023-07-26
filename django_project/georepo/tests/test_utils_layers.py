from django.test import TestCase, override_settings
from georepo.utils import absolute_path
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF
)
from georepo.utils.layers import check_properties


class TestCheckProperties(TestCase):

    def setUp(self) -> None:
        self.entity_type = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
        from dashboard.tests.model_factories import (
            LayerUploadSessionF
        )
        self.layer_upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_check_properties(self):
        from dashboard.tests.model_factories import (
            LayerFileF
        )
        layer_file_1 = LayerFileF.create(
            layer_upload_session=self.layer_upload_session,
            layer_type='GEOJSON',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_1.geojson')
            )
        )
        errors, feature_count = check_properties(layer_file_1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(feature_count, 1)
        layer_file_2 = LayerFileF.create(
            layer_upload_session=self.layer_upload_session,
            layer_type='SHAPEFILE',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'shapefile_dataset', 'shp_1_1.zip')
            )
        )
        errors, feature_count = check_properties(layer_file_2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(feature_count, 3)
        layer_file_3 = LayerFileF.create(
            layer_upload_session=self.layer_upload_session,
            layer_type='GEOPACKAGE',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'gpkg_dataset', 'gpkg_1_1.gpkg')
            )
        )
        errors, feature_count = check_properties(layer_file_3)
        self.assertEqual(len(errors), 0)
        self.assertEqual(feature_count, 3)
        errors, feature_count = check_properties(None)
        self.assertEqual(len(errors), 0)
        self.assertEqual(feature_count, 0)
        layer_file_4 = LayerFileF.create(
            layer_upload_session=self.layer_upload_session,
            layer_type='GEOJSON',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_0_2.geojson')
            )
        )
        errors, feature_count = check_properties(layer_file_4)
        self.assertEqual(len(errors), 0)
        self.assertEqual(feature_count, 0)
