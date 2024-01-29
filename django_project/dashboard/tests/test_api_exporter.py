import mock
from django.urls import reverse
from django.utils import timezone
from georepo.models.dataset import Dataset
from georepo.models.base_task_request import PENDING
from georepo.models.export_request import (
    ExportRequest,
    GEOJSON_EXPORT_TYPE,
    ExportRequestStatusText
)
from georepo.tests.common import (
    BaseDatasetViewTest,
    mocked_process
)
from dashboard.api_views.exporter import (
    ExportHistoryList,
    ExportRequestDetail,
    ExportRequestMetadata
)
from georepo.utils.tile_configs import populate_tile_configs


class TestExporterAPI(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()
        populate_tile_configs(self.dataset.id)

    def test_get_export_history_list(self):
        kwargs = {
            'id': str(self.dataset_view.id)
        }
        request = self.factory.get(
            reverse('exporter-history-list',
                    kwargs=kwargs)
        )
        request.user = self.superuser
        view = ExportHistoryList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        export_request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        request = self.factory.get(
            reverse('exporter-history-list',
                    kwargs=kwargs)
        )
        request.user = self.superuser
        view = ExportHistoryList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], export_request.id)

    def test_get_export_request_detail(self):
        export_request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        kwargs = {
            'id': str(self.dataset_view.id)
        }
        request = self.factory.get(
            reverse('exporter-request-detail',
                    kwargs=kwargs) + f'?request_id={export_request.id}'
        )
        request.user = self.superuser
        view = ExportRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], export_request.id)

    @mock.patch('georepo.tasks.dataset_view.'
                'dataset_view_exporter.apply_async')
    def test_create_export_request(self, mocked_task):
        mocked_task.side_effect = mocked_process
        kwargs = {
            'id': str(self.dataset_view.id)
        }
        # test invalid format
        data = {
            'is_simplified_entities': False,
            'simplification_zoom_level': None,
            'format': 'invalid_format',
        }
        request = self.factory.post(
            reverse(
                'exporter-request-detail', kwargs=kwargs
            ),
            data,
            format='json'
        )
        request.user = self.superuser
        view = ExportRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)
        self.assertIn('Invalid format type', response.data['detail'])
        mocked_task.assert_not_called()
        # test simplification not ready
        self.dataset.simplification_sync_status = (
            Dataset.SyncStatus.OUT_OF_SYNC
        )
        self.dataset.save()
        data = {
            'is_simplified_entities': True,
            'simplification_zoom_level': 1,
            'format': 'GEOJSON'
        }
        request = self.factory.post(
            reverse(
                'exporter-request-detail', kwargs=kwargs
            ),
            data,
            format='json'
        )
        request.user = self.superuser
        view = ExportRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)
        self.assertIn('out of sync simplified entities',
                      response.data['detail'])
        mocked_task.assert_not_called()
        # test invalid zoom level
        self.dataset.simplification_sync_status = (
            Dataset.SyncStatus.SYNCED
        )
        self.dataset.save()
        data = {
            'is_simplified_entities': True,
            'simplification_zoom_level': 122,
            'format': 'GEOJSON'
        }
        request = self.factory.post(
            reverse(
                'exporter-request-detail', kwargs=kwargs
            ),
            data,
            format='json'
        )
        request.user = self.superuser
        view = ExportRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)
        self.assertIn('Invalid simplification zoom level',
                      response.data['detail'])
        mocked_task.assert_not_called()
        # test success
        data = {
            'filters': {
                'level': [0, 1]
            },
            'is_simplified_entities': False,
            'simplification_zoom_level': None,
            'format': 'GEOJSON'
        }
        request = self.factory.post(
            reverse(
                'exporter-request-detail', kwargs=kwargs
            ),
            data,
            format='json'
        )
        request.user = self.superuser
        view = ExportRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 201)
        mocked_task.assert_called_once()
        self.assertIn('id', response.data)
        export_request = ExportRequest.objects.filter(
            id=response.data['id']
        ).first()
        self.assertTrue(export_request)
        self.assertTrue(export_request.task_id)
        self.assertEqual(export_request.status, PENDING)
        self.assertEqual(export_request.status_text,
                         str(ExportRequestStatusText.WAITING))
        self.assertIn('level', export_request.filters)
        self.assertEqual(export_request.filters['level'],
                         data['filters']['level'])
        self.assertEqual(export_request.source, 'dashboard')


    def test_get_export_request_metadata(self):
        kwargs = {
            'id': str(self.dataset_view.id)
        }
        request = self.factory.get(
            reverse('exporter-request-metadata',
                    kwargs=kwargs) + '?session_id=123123'
        )
        request.user = self.superuser
        view = ExportRequestMetadata.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['filters'])
        self.assertFalse(response.data['is_simplification_available'])
        self.assertTrue(len(response.data['tiling_configs']) > 0)
