import os
import mock
from django.conf import settings
from georepo.tests.common import BaseDatasetViewTest
from georepo.models.dataset_view import DatasetViewResource
from georepo.utils.centroid_exporter import CentroidExporter
from georepo.utils.azure_blob_storage import StorageContainerClient


def check_file_exists(file_path):
    exists = False
    if settings.USE_AZURE and StorageContainerClient:
        bc = StorageContainerClient.get_blob_client(blob=file_path)
        exists = bc.exists()
    else:
        exists = os.path.isfile(file_path)
    return exists


def mocked_convert_geojson(file_path, output_dir, exported_name):
    return file_path


class TestCentroidExporter(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()

    @mock.patch('georepo.utils.centroid_exporter.'
                'convert_geojson_to_pbf')
    def test_resource_centroid(self, mocked_func):
        mocked_func.side_effect = mocked_convert_geojson
        resource = DatasetViewResource.objects.filter(
            dataset_view=self.dataset_view,
            privacy_level=4
        ).first()
        exporter = CentroidExporter(resource)
        exporter.output_suffix = '.geojson'
        exporter.init_exporter()
        exporter.run()
        resource.refresh_from_db()
        self.assertEqual(len(resource.centroid_files), 2)
        self.assertFalse(os.path.exists(exporter.get_tmp_output_dir(False)))
        for exporter_file in resource.centroid_files:
            self.assertTrue(check_file_exists(exporter_file['path']))
