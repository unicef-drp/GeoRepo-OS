import mock
import json
from django.urls import reverse
from django.utils import timezone

from georepo.models import SearchIdRequest
from georepo.models.base_task_request import (
    PENDING,
    DONE
)
from georepo.tasks.search_id import (
    process_search_id_request
)
from georepo.api_views.entity_view import (
    ViewEntityBatchSearchId,
    ViewEntityBatchSearchIdStatus
)
from georepo.tests.common import (
    BaseDatasetViewTest,
    mocked_process
)


class TestSearchId(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()

    def test_process_search_id_request(self):
        id_request = SearchIdRequest.objects.create(
            status=PENDING,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            parameters=f'({self.dataset_view.id},)',
            input_id_type=self.pCode.name,
            output_id_type='ucode',
            input=['PAK']
        )
        process_search_id_request(id_request.id)
        id_request.refresh_from_db()
        self.assertEqual(id_request.status, DONE)
        self.assertTrue(id_request.output_file)
        self.assertTrue(
            id_request.output_file.storage.exists(
                id_request.output_file.name)
        )
        id_request.delete()
        # test without output_id_type
        id_request = SearchIdRequest.objects.create(
            status=PENDING,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            parameters=f'({self.dataset_view.id},)',
            input_id_type=self.pCode.name,
            output_id_type=None,
            input=['PAK']
        )
        process_search_id_request(id_request.id)
        id_request.refresh_from_db()
        self.assertEqual(id_request.status, DONE)
        self.assertTrue(id_request.output_file)
        self.assertTrue(
            id_request.output_file.storage.exists(
                id_request.output_file.name)
        )
        f = id_request.output_file.open()
        data = json.load(f)
        # match the uuid and concept_uuid from PAK_V2
        self.assertEqual(
            str(self.pak0_2.uuid), data['PAK'][0]['concept_uuid'])
        self.assertEqual(
            str(self.pak0_2.uuid_revision), data['PAK'][0]['uuid'])
        f.close()
        id_request.delete()

    @mock.patch('georepo.api_views.entity_view.'
                'process_search_id_request.delay')
    def test_submit_search_id_request(self, mocked_task):
        mocked_task.side_effect = mocked_process
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'input_type': self.pCode.name,
        }
        request = self.factory.post(
            reverse(
                'v1:batch-search-view-by-id',
                kwargs=kwargs
            ) + '?return_type=ucode',
            data=['PAK'],
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityBatchSearchId.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        mocked_task.assert_called_once()
        self.assertIn('request_id', response.data)
        self.assertIn('status_url', response.data)
        id_request = SearchIdRequest.objects.get(
            uuid=response.data['request_id'])
        self.assertEqual(id_request.status, PENDING)
        status_kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'request_id': response.data['request_id']
        }
        request = self.factory.get(
            reverse(
                'v1:batch-result-search-view-by-id',
                kwargs=status_kwargs
            ),
        )
        request.user = self.superuser
        view = ViewEntityBatchSearchIdStatus.as_view()
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], PENDING)
        self.assertFalse(response.data['output_url'])
        process_search_id_request(id_request.id)
        id_request.refresh_from_db()
        self.assertEqual(id_request.status, DONE)
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], DONE)
        self.assertTrue(response.data['output_url'])
