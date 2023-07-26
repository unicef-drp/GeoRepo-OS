from django.test import TestCase
from django.contrib.auth import get_user_model
from azure_auth.backends import AzureAuthBackend
from azure_auth.models import RegisteredDomain

UserModel = get_user_model()


class TestAzureAuthBackend(TestCase):

    def test_get_user_from_user_model(self):
        # create live.com#test@test.com user
        user1 = UserModel.objects.create(
            username='test@test.com',
            email='test@test.com'
        )
        user = AzureAuthBackend.get_user_from_user_model({
            'email': 'live.com#test@test.com'
        })
        self.assertEqual(user1.id, user.id)
        user = AzureAuthBackend.get_user_from_user_model({
            'email': 'test@test.com'
        })
        self.assertEqual(user1.id, user.id)

    def test_create_new_user(self):
        RegisteredDomain.objects.create(
            domain='test.com'
        )
        user = AzureAuthBackend.create_new_user({
            'email': 'live.com#test@test.com'
        })
        self.assertTrue(user.id)
        self.assertEqual(user.username, 'test@test.com')
        self.assertEqual(user.email, 'test@test.com')
