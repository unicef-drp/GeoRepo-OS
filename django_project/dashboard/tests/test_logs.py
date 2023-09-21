import uuid

from django.shortcuts import reverse
from rest_framework.test import APITestCase, APIRequestFactory

from dashboard.api_views.logs import ExportLogs
from dashboard.models.entity_upload import EntityUploadStatusLog
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    GeographicalEntityF,
    EntityUploadF
)
from georepo.models.dataset_view import DatasetViewResourceLog
from georepo.tests.model_factories import (
    DatasetF,
    DatasetViewF,
    LanguageF,
    UserF
)
from georepo.utils.dataset_view import (
    create_sql_view,
    init_view_privacy_level
)


class TestExportLogs(APITestCase):
    def setUp(self) -> None:
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanish'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.dataset = DatasetF.create()
        self.factory = APIRequestFactory()
        self.log_1 = {
            "find_country_max_level": {
                "count": 1,
                "avg_time": 0.038579702377319336,
                "total_time": 0.038579702377319336
            },
            "ValidateUploadSession.post": {
                "count": 1,
                "avg_time": 0.03463172912597656,
                "total_time": 0.03463172912597656
            }
        }
        self.log_2 = {
            "find_country_max_level": {
                "count": 1,
                "avg_time": 0.038579702377319336,
                "total_time": 0.038579702377319336
            },
            "AdminBoundaryMatching.run": {
                "count": 1,
                "avg_time": 0.9563043117523193,
                "total_time": 0.9563043117523193
            }
        }

    def setup_upload(self):
        self.layer_upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        entity_1 = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            level=0,
            dataset=self.dataset,
            internal_code='GO',
            label='Entity 1',
            is_approved=True,
            is_latest=True,
            unique_code='GO'
        )
        self.entity_upload_1 = EntityUploadF.create(
            original_geographical_entity=entity_1,
            upload_session=self.layer_upload_session,
            status='Valid'
        )
        EntityUploadStatusLog.objects.create(
            layer_upload_session=self.layer_upload_session,
            logs=self.log_1
        )
        EntityUploadStatusLog.objects.create(
            layer_upload_session=self.layer_upload_session,
            entity_upload_status=self.entity_upload_1,
            logs=self.log_2
        )

    def setup_dataset_view(self):
        self.dataset_view_1 = DatasetViewF.create(
            name='custom',
            created_by=self.superuser,
            dataset=self.dataset,
            is_static=False,
            query_string=(
                'SELECT * FROM georepo_geographicalentity where '
                f"dataset_id={self.dataset.id} AND revision_number=1"
            )
        )
        create_sql_view(self.dataset_view_1)
        init_view_privacy_level(self.dataset_view_1)

    def test_log_layer_upload(self):
        self.setup_upload()
        request = self.factory.get(
            reverse('export-log-csv', args=['layer', self.layer_upload_session.id])
        )
        request.user = self.superuser
        view = ExportLogs.as_view()
        response = view(request, 'layer', self.layer_upload_session.id)
        contents = response.streaming_content
        content_list = []
        for content in contents:
            content_list.append(content.decode('utf-8').strip().split(','))

        self.assertEqual(len(content_list), 4)
        self.assertEqual(
            content_list,
            [
                ['Action', 'Call Count', 'Average Time (s)', 'Total Time (s)'],
                ['Find Country Max Level', '2', '0.03', '0.07'],
                ['Validate Upload Session - Post', '1', '0.03', '0.03'],
                ['Admin Boundary Matching - Run', '1', '0.95', '0.95']
            ]
        )

    def test_log_entity_upload(self):
        self.setup_upload()
        request = self.factory.get(
            reverse('export-log-csv', args=['entity', self.entity_upload_1.id])
        )
        request.user = self.superuser
        view = ExportLogs.as_view()
        response = view(request, 'entity', self.entity_upload_1.id)
        contents = response.streaming_content
        content_list = []
        for content in contents:
            content_list.append(content.decode('utf-8').strip().split(','))

        self.assertEqual(len(content_list), 3)
        self.assertEqual(
            content_list,
            [
                ['Action', 'Call Count', 'Average Time (s)', 'Total Time (s)'],
                ['Find Country Max Level', '1', '0.03', '0.03'],
                ['Admin Boundary Matching - Run', '1', '0.95', '0.95']
            ]
        )

    def test_log_view(self):
        self.setup_dataset_view()

        DatasetViewResourceLog.objects.create(
            dataset_view=self.dataset_view_1,
            logs=self.log_1
        )
        view_resource = self.dataset_view_1.datasetviewresource_set.all().first()
        DatasetViewResourceLog.objects.create(
            dataset_view=self.dataset_view_1,
            dataset_view_resource=view_resource,
            logs=self.log_2
        )

        request = self.factory.get(
            reverse('export-log-csv', args=['view', self.dataset_view_1.id])
        )
        request.user = self.superuser
        view = ExportLogs.as_view()
        response = view(request, 'view', self.dataset_view_1.id)
        contents = response.streaming_content
        content_list = []
        for content in contents:
            content_list.append(content.decode('utf-8').strip().split(','))
        self.assertEqual(len(content_list), 4)
        self.assertEqual(
            content_list,
            [
                ['Action', 'Call Count', 'Average Time (s)', 'Total Time (s)'],
                ['Find Country Max Level', '2', '0.03', '0.07'],
                ['Validate Upload Session - Post', '1', '0.03', '0.03'],
                ['Admin Boundary Matching - Run', '1', '0.95', '0.95']
            ]
        )
