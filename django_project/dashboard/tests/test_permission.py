from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.urls import reverse
from georepo.tests.model_factories import (
    UserF
)
from dashboard.api_views.permission import FetchPrivacyLevelLabels


class TestPermissionAPIViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(
            first_name='user',
            last_name='_1',
            email='user_1@test.com',
            username='user_1'
        )
        self.superuser = UserF.create(is_superuser=True)

    def test_fetch_privacy_levels(self):
        request = self.factory.get(
            reverse('fetch-privacy-levels')
        )
        request.user = self.superuser
        view = FetchPrivacyLevelLabels.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertIn(1, response.data)
        self.assertIn(2, response.data)
