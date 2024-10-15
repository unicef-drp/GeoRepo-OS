import mock
from datetime import datetime
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from dashboard.api_views.notification import NotificationList
from georepo.tests.model_factories import UserF
from dashboard.tests.model_factories import NotificationF
from dashboard.models.notification import (
    Notification,
    NOTIF_TYPE_BOUNDARY_MATCHING
)
from dashboard.models.maintenance import Maintenance


class TestNotification(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_notification_list(self):
        user_1 = UserF.create(username='test_1')
        user_2 = UserF.create(username='test_2')
        request = self.factory.get(
            reverse('notification-list')
        )
        request.user = user_1
        view = NotificationList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['notifications']), 0)
        NotificationF.create(
            type=NOTIF_TYPE_BOUNDARY_MATCHING,
            message='Your data is ready!',
            recipient=user_1
        )
        NotificationF.create(
            type=NOTIF_TYPE_BOUNDARY_MATCHING,
            message='Your data2 is ready!',
            recipient=user_2
        )
        request = self.factory.get(
            reverse('notification-list')
        )
        request.user = user_1
        view = NotificationList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['notifications']), 1)
        self.assertEqual(
            response.data['notifications'][0]['message'],
            'Your data is ready!')
        self.assertEqual(Notification.objects.filter(
            recipient=user_1).count(), 0)
        self.assertEqual(Notification.objects.filter(
            recipient=user_2).count(), 1)

    @mock.patch('dashboard.api_views.notification.timezone')
    def test_check_for_maintenance(self, mocked_datetime):
        user_1 = UserF.create()
        mocked_datetime.now.return_value = datetime.strptime(
            '2023-01-06 06:10:00.000 +0800',
            '%Y-%m-%d %H:%M:%S.%f %z'
        )
        request = self.factory.get(
            reverse('notification-list')
        )
        request.user = user_1
        view = NotificationList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_maintenance'])
        # create 1 maintenance
        maintenance = Maintenance.objects.create(
            message='Test',
            scheduled_from_date='2023-01-06 06:00:00.000 +0800',
            created_by=user_1
        )
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['has_maintenance'])
        self.assertEqual(response.data['maintenance']['id'], maintenance.id)
        maintenance.scheduled_from_date = '2023-01-06 07:00:00.000 +0800'
        maintenance.save()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_maintenance'])
