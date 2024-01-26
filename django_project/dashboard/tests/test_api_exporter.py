from django.urls import reverse
from georepo.tests.common import (
    BaseDatasetViewTest,
    DummyTask,
    mocked_process
)
from dashboard.api_views.exporter import (
    ExportHistoryList,
    ExportRequestDetail,
    ExportRequestMetadata
)


class TestExporterAPI(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()

    def test_get_export_history_list(self):
        pass

    def test_get_export_request_detail(self):
        pass

    def test_create_export_request(self):
        pass

    def test_get_export_request_metadata(self):
        kwargs = {
            'id': str(self.dataset_view.id)
        }
        request = self.factory.get(
            reverse('exporter-request-metadata',
                    kwargs=kwargs) + f'?session_id=123123'
        )
        request.user = self.superuser
        view = ExportRequestMetadata.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
