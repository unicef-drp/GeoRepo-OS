import copy

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory
from django.test import TestCase
from django.urls import reverse


from dashboard.api_views.users import UserDetail
from georepo.models.role import GeorepoRole
from georepo.tests.model_factories import (
    UserF
)


class TestUserCreate(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)
        self.creator = UserF.create()
        self.User = get_user_model()
        self.payload = {
            'first_name': 'User',
            'last_name': 'Test 1',
            'username': 'user_test_1',
            'email': 'user_test_1@domain.com',
            'password': 'user_test_1',
            'role': 'Creator',
        }

    def test_create_anonymous_user(self):
        request = self.factory.post(
            reverse('user-create')
        )
        request.user = AnonymousUser()
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 401)

    def test_create_user_creator(self):
        request = self.factory.post(
            reverse('user-create')
        )
        request.user = self.creator
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)

    def test_create_role_not_exist(self):
        request = self.factory.post(
            reverse('user-create')
        )
        request.user = self.superuser
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Invalid role!')

    def test_create_user_creator_success(self):
        payload = copy.deepcopy(self.payload)
        request = self.factory.post(
            reverse('user-create'),
            payload
        )
        request.user = self.superuser
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(username='user_test_1')
        self.assertEqual(response.data, {'id': user.id})
        self.assertEqual(user.is_superuser, False)
        self.assertEqual(user.is_staff, False)
        self.assertEqual(user.georeporole.type, GeorepoRole.RoleType.CREATOR)
        self.assertTrue(user.check_password(payload['password']))

    def test_create_superuser_success(self):
        payload = copy.deepcopy(self.payload)
        payload['role'] = 'Admin'
        request = self.factory.post(
            reverse('user-create'),
            payload
        )
        request.user = self.superuser
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(username='user_test_1')
        self.assertEqual(response.data, {'id': user.id})
        self.assertEqual(user.is_superuser, True)
        self.assertEqual(user.is_staff, True)
        self.assertEqual(user.georeporole.type, GeorepoRole.RoleType.CREATOR)
        self.assertTrue(user.check_password(payload['password']))

    def test_create_superuser_viewer(self):
        payload = copy.deepcopy(self.payload)
        payload['role'] = 'Viewer'
        request = self.factory.post(
            reverse('user-create'),
            payload
        )
        request.user = self.superuser
        view = UserDetail.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 201)

        user = self.User.objects.get(username='user_test_1')
        self.assertEqual(response.data, {'id': user.id})
        self.assertEqual(user.is_superuser, False)
        self.assertEqual(user.is_staff, False)
        self.assertEqual(user.georeporole.type, GeorepoRole.RoleType.VIEWER)
        self.assertTrue(user.check_password(payload['password']))
