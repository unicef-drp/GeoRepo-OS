from django.test import TestCase
from datetime import datetime
from rest_framework.test import APIRequestFactory
from django.urls import reverse
from georepo.tests.model_factories import (
    UserF
)
from georepo.models.access_request import UserAccessRequest
from dashboard.api_views.access_request import (
    AccessRequestList,
    AccessRequestDetail,
    SubmitPermissionAccessRequest
)


class TestAccessRequestAPIViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(
            first_name='user',
            last_name='_1',
            email='user_1@test.com',
            username='user_1'
        )
        self.superuser = UserF.create(is_superuser=True)

    def test_get_list(self):
        kwargs = {
            'type': 'permission'
        }
        request = self.factory.get(
            reverse('fetch-access-request-list', kwargs=kwargs)
        )
        request.user = self.superuser
        view = AccessRequestList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_approval(self):
        request_obj = UserAccessRequest.objects.create(
            type=UserAccessRequest.RequestType.NEW_PERMISSIONS,
            status=UserAccessRequest.RequestStatus.PENDING,
            submitted_on=datetime.now(),
            requester_first_name=self.user_1.first_name,
            requester_last_name=self.user_1.last_name,
            requester_email=self.user_1.email,
            description='Test',
            request_by=self.user_1
        )
        kwargs = {
            'request_id': request_obj.id
        }
        request = self.factory.get(
            reverse('fetch-access-request-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        view = AccessRequestDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        data = {
            'is_approve': True,
            'remarks': 'TestRemarks'
        }
        request = self.factory.post(
            reverse('fetch-access-request-detail', kwargs=kwargs),
            data, format='json'
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['requester_id'], self.user_1.id)
        request_obj = UserAccessRequest.objects.get(id=request_obj.id)
        self.assertEqual(request_obj.status,
                         UserAccessRequest.RequestStatus.APPROVED)

    def test_submit(self):
        data = {
            'description': 'Request access for dataset'
        }
        request = self.factory.post(
            reverse('create-permission-access-request'),
            data=data, format='json'
        )
        request.user = self.user_1
        view = SubmitPermissionAccessRequest.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 201)
        request = self.factory.get(
            reverse('create-permission-access-request')
        )
        request.user = self.user_1
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['has_pending_request'], True)
