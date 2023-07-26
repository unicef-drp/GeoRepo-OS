import uuid
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory, APIClient

from dashboard.tests.model_factories import EntityUploadF, LayerUploadSessionF
from dashboard.api_views.entity import EntityRevisionList
from georepo.tests.model_factories import (
    GeographicalEntityF,
    DatasetF, UserF
)


class TestRevisionApiViews(TestCase):
    def setUp(self) -> None:
        self.dataset = DatasetF.create()
        self.parent = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            level=0,
            dataset=self.dataset,
            internal_code='ISO'
        )
        child_uuid = str(uuid.uuid4())
        self.child_entity = GeographicalEntityF.create(
            parent=self.parent,
            uuid=child_uuid,
            start_date='2022-10-10',
            level=1,
            dataset=self.dataset,
            revision_number=1
        )
        self.child_entity_2 = GeographicalEntityF.create(
            parent=self.parent,
            uuid=child_uuid,
            start_date='2022-10-11',
            level=1,
            dataset=self.dataset,
            revision_number=2,
            is_approved=False
        )
        self.child_entity_3 = GeographicalEntityF.create(
            parent=self.parent,
            uuid=child_uuid,
            start_date='2022-10-12',
            level=1,
            dataset=self.dataset,
            revision_number=3
        )
        self.factory = APIRequestFactory()

    def test_get_revision(self):
        request = self.factory.get(
            reverse('entity-revisions') + f'?id={self.child_entity.id}'
        )

        view = EntityRevisionList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data[-1]['id'], self.child_entity.id)
        self.assertFalse(response_data[1]['reviewable'])

    def test_get_revision_as_superuser(self):
        user = UserF.create(
            username='test', is_superuser=True)
        client = APIClient()
        child_entity_4 = GeographicalEntityF.create(
            parent=self.parent,
            uuid=self.child_entity.uuid,
            start_date='2022-10-15',
            level=1,
            dataset=self.dataset,
            revision_number=4
        )
        upload_session = LayerUploadSessionF.create(
            uploader=user
        )
        EntityUploadF.create(
            revised_geographical_entity=child_entity_4,
            upload_session=upload_session
        )
        client.force_authenticate(user=user)
        response = client.get(
            reverse('entity-revisions') + f'?id={self.child_entity.id}'
        )
        response_data = response.data
        self.assertTrue(response_data[1]['reviewable'])
        self.assertTrue(response_data[0]['uploader'], user.username)
