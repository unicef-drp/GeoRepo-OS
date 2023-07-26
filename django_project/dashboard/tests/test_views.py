from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.views.uploader import UploaderView
from georepo.tests.model_factories import UserF


class TestViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_uploader_view_not_logged_in(self):
        request = self.factory.get(
            reverse('upload')
        )
        request.user = AnonymousUser()
        view = UploaderView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 302)

    def test_uploader_view(self):
        user = UserF.create(username='test')
        request = self.factory.get(
            reverse('upload')
        )
        request.user = user
        view = UploaderView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
