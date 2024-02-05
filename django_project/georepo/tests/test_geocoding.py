import json
import mock
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from georepo.utils import absolute_path
from georepo.models.base_task_request import (
    PENDING, DONE
)
from georepo.models.geocoding_request import (
    GeocodingRequest, GEOJSON
)
from georepo.tasks.geocoding import (
    get_containment_check_query,
    process_geocoding_request
)
from georepo.api_views.entity_view import (
    ViewEntityBatchGeocoding,
    ViewEntityBatchGeocodingStatus,
    ViewEntityBatchGeocodingResult
)
from georepo.tests.common import (
    BaseDatasetViewTest,
    mocked_process
)


class TestProcessGeocodingRequest(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()

    def test_get_containment_check_query(self):
        sql, query_values = get_containment_check_query(
            self.dataset_view, 'tmp.test_table', 'ST_Intersects', 0,
            4, 'ucode', 0
        )
        self.assertIn('ST_Intersects(s.geometry, tmp_entity.geometry)', sql)
        self.assertIn('from tmp.test_table s', sql)
        self.assertIn(str(self.dataset_view.uuid), sql)
        self.assertIn(self.dataset.id, query_values)
        self.assertIn(4, query_values)

    @mock.patch('georepo.api_views.entity_view.'
                'process_geocoding_request.delay')
    def test_submit_batch_geocoding(self, mocked_task):
        mocked_task.side_effect = mocked_process
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': 'ST_Intersects',
            'distance': 0,
            'admin_level': 0,
            'id_type': 'ucode'
        }
        test_file_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_test_points.geojson')
        data = open(test_file_path, 'rb')
        file = SimpleUploadedFile(
            content=data.read(),
            name=data.name,
            content_type='multipart/form-data'
        )
        request = self.factory.post(
            reverse(
                'v1:batch-geocoding',
                kwargs=kwargs
            ),
            data={
                'file': file
            }
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocoding.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        mocked_task.assert_called_once()
        self.assertIn('request_id', response.data)
        self.assertIn('status_url', response.data)
        geocoding_request = GeocodingRequest.objects.filter(
            uuid=response.data['request_id']
        ).first()
        self.assertTrue(geocoding_request)
        self.assertEqual(geocoding_request.status, PENDING)
        self.assertEqual(geocoding_request.file_type, GEOJSON)
        self.assertTrue(geocoding_request.file)
        params = (
            f'({str(self.dataset_view.id)},\'ST_Intersects\','
            f'0,\'ucode\',0,False)'
        )
        self.assertEqual(geocoding_request.parameters, params)
        self.assertTrue(geocoding_request.task_id)
        process_geocoding_request(geocoding_request.id)
        geocoding_request.refresh_from_db()
        self.assertEqual(geocoding_request.status, DONE)
        self.assertTrue(geocoding_request.output_file)
        self.assertEqual(geocoding_request.feature_count, 3)
        status_kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'request_id': response.data['request_id']
        }
        request = self.factory.get(
            reverse(
                'v1:check-status-batch-geocoding',
                kwargs=status_kwargs
            )
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocodingStatus.as_view()
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], DONE)
        self.assertIn('output_url', response.data)
        self.assertTrue(response.data['output_url'])
        request = self.factory.get(
            reverse(
                'v1:get-result-batch-geocoding',
                kwargs=status_kwargs
            )
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocodingResult.as_view()
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertTrue(response.has_header('Content-Type'))
        # check for output result
        with geocoding_request.output_file.open('rb') as json_data:
            features = json.load(json_data)
            self.assertEqual(len(features['features']), 3)
            feat_1 = features['features'][0]
            self.assertIn('ucode', feat_1['properties'])
            self.assertEqual(len(feat_1['properties']['ucode']), 1)
            self.assertEqual(feat_1['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_2 = features['features'][1]
            self.assertIn('ucode', feat_2['properties'])
            self.assertEqual(len(feat_2['properties']['ucode']), 1)
            self.assertEqual(feat_2['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_3 = features['features'][2]
            self.assertIn('ucode', feat_3['properties'])
            self.assertEqual(len(feat_3['properties']['ucode']), 0)

    @mock.patch('georepo.api_views.entity_view.'
                'process_geocoding_request.delay')
    def test_submit_batch_geocoding_nearest(self, mocked_task):
        mocked_task.side_effect = mocked_process
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': 'ST_Intersects',
            'distance': 0,
            'admin_level': 0,
            'id_type': 'ucode'
        }
        test_file_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_test_points.geojson')
        data = open(test_file_path, 'rb')
        file = SimpleUploadedFile(
            content=data.read(),
            name=data.name,
            content_type='multipart/form-data'
        )
        request = self.factory.post(
            reverse(
                'v1:batch-geocoding',
                kwargs=kwargs
            ) + '?find_nearest=true',
            data={
                'file': file
            }
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocoding.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        mocked_task.assert_called_once()
        self.assertIn('request_id', response.data)
        self.assertIn('status_url', response.data)
        geocoding_request = GeocodingRequest.objects.filter(
            uuid=response.data['request_id']
        ).first()
        self.assertTrue(geocoding_request)
        self.assertEqual(geocoding_request.status, PENDING)
        self.assertEqual(geocoding_request.file_type, GEOJSON)
        self.assertTrue(geocoding_request.file)
        params = (
            f'({str(self.dataset_view.id)},\'ST_Intersects\','
            f'0,\'ucode\',0,True)'
        )
        self.assertEqual(geocoding_request.parameters, params)
        self.assertTrue(geocoding_request.task_id)
        process_geocoding_request(geocoding_request.id)
        geocoding_request.refresh_from_db()
        self.assertEqual(geocoding_request.status, DONE)
        self.assertTrue(geocoding_request.output_file)
        self.assertEqual(geocoding_request.feature_count, 3)
        # check for output result
        with geocoding_request.output_file.open('rb') as json_data:
            features = json.load(json_data)
            self.assertEqual(len(features['features']), 3)
            feat_1 = features['features'][0]
            self.assertIn('ucode', feat_1['properties'])
            self.assertEqual(len(feat_1['properties']['ucode']), 1)
            self.assertEqual(feat_1['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_2 = features['features'][1]
            self.assertIn('ucode', feat_2['properties'])
            self.assertEqual(len(feat_2['properties']['ucode']), 1)
            self.assertEqual(feat_2['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_3 = features['features'][2]
            self.assertIn('ucode', feat_3['properties'])
            self.assertEqual(len(feat_3['properties']['ucode']), 1)
            self.assertEqual(feat_3['properties']['ucode'][0],
                             self.pak0_2.ucode)
