import datetime
from django.test import TestCase

from georepo.tests.model_factories import UserF
from georepo.models.base_task_request import PENDING
from georepo.models.search_id_request import SearchIdRequest
from georepo.models.geocoding_request import GeocodingRequest
from georepo.tasks.remove_task_request import remove_old_task_requests


class TestRemoveOldTaskRequest(TestCase):

    def setUp(self):
        self.superuser = UserF.create(is_superuser=True)

    def test_remove_old_task_requests(self):
        SearchIdRequest.objects.create(
            status=PENDING,
            submitted_on=datetime.datetime(2000, 8, 14, 8, 8, 8),
            submitted_by=self.superuser,
            parameters='(1,)',
            input_id_type='PCode',
            output_id_type='ucode',
            input=['PAK']
        )
        GeocodingRequest.objects.create(
            status=PENDING,
            submitted_on=datetime.datetime(2000, 8, 14, 8, 8, 8),
            submitted_by=self.superuser,
            parameters='(1,)',
        )
        remove_old_task_requests()
        self.assertFalse(SearchIdRequest.objects.exists())
        self.assertFalse(GeocodingRequest.objects.exists())
