from django.test import TestCase, override_settings
from georepo.utils import absolute_path

from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF
)
from georepo.utils.load_layer_file import (
    load_layer_file
)


class TestLoadLayerFile(TestCase):

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
    def test_load_layer_file_geojson(self):
        geojson_0_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_1.geojson')
        success, error = load_layer_file(
            'GEOJSON',
            geojson_0_1_path,
            0,
            self.entity_type,
            'name_{level}',
            self.dataset.label,
            'code_{level}',
            self.layer_upload_session.id
        )
        self.assertEqual(success, True)
        self.assertEqual(error, '')
        from dashboard.models import LayerUploadSession
        session = LayerUploadSession.objects.get(
            id=self.layer_upload_session.id
        )
        self.assertIsNotNone(session.progress)
        self.assertIsNotNone(session.message)
        self.assertTrue(len(session.message) > 0)
        success, error = load_layer_file(
            'GEOJSON',
            geojson_0_1_path,
            0,
            self.entity_type,
            'name123_{level}',
            self.dataset.label,
            'code123_{level}',
            self.layer_upload_session.id
        )
        self.assertEqual(success, False)
        self.assertEqual(
            error,
            'Label or code format not found in the layer'
        )


    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_load_layer_file_shapefile(self):
        shapefile_path = absolute_path(
            'georepo', 'tests',
            'shapefile_dataset', 'shp_1_1.zip')
        success, error = load_layer_file(
            'SHAPEFILE',
            shapefile_path,
            1,
            self.entity_type,
            'name_{level}',
            self.dataset.label,
            'code_{level}'
        )
        self.assertEqual(success, True)
        self.assertEqual(error, '')


    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_load_layer_file_gpkg(self):
        gpkgfile_path = absolute_path(
            'georepo', 'tests',
            'gpkg_dataset', 'gpkg_1_1.gpkg')
        success, error = load_layer_file(
            'GEOPACKAGE',
            gpkgfile_path,
            1,
            self.entity_type,
            'name_{level}',
            self.dataset.label,
            'code_{level}'
        )
        self.assertEqual(success, True)
        self.assertEqual(error, '')
