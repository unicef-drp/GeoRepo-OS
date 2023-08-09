from django.test import TestCase, override_settings
import mock
import base64
import json
import time
import msal
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APIRequestFactory
from django.contrib.sessions.backends.db import SessionStore
from azure_auth.models import ThirdPartyApplication
from azure_auth.api_views import AzureRefreshToken
from azure_auth.configuration import _AzureAuthConfig

UserModel = get_user_model()
mocked_azure_settings = {
    'CLIENT_ID': 'abcdef',
    'CLIENT_SECRET': 'random',
    'TENANT_NAME': 'tenant',
    'POLICY_NAME': 'policy_name'
}
mocked_azure_config = _AzureAuthConfig(
    config=mocked_azure_settings).parse_settings()


def build_id_token(
        iss="issuer", sub="subject", aud="my_client_id", exp=None, iat=None,
        **claims):  # AAD issues "preferred_username", ADFS issues "upn"
    return "header.%s.signature" % base64.b64encode(
        json.dumps(
            dict({
                "iss": iss,
                "sub": sub,
                "aud": aud,
                "exp": exp or (time.time() + 100),
                "iat": iat or time.time(),
            }, **claims)
        ).encode()).decode('utf-8')


# kwargs: Pass-through: refresh_token, foci, id_token, error, refresh_in, ...
# simulate a response from AAD
def build_response(
        uid=None, utid=None,  # If present, they will form client_info
        access_token=None, expires_in=3600, token_type="some type",
        **kwargs):
    response = {}
    if uid and utid:  # Mimic the AAD behavior for "client_info=1" request
        response["client_info"] = base64.b64encode(
            json.dumps({
                "uid": uid,
                "utid": utid,
            }).encode()
        ).decode('utf-8')
    if access_token:
        response.update({
            "access_token": access_token,
            "expires_in": expires_in,
            "token_type": token_type,
        })
    # Pass-through key-value pairs as top-level fields
    response.update(kwargs)
    return response


@override_settings(AZURE_AUTH=mocked_azure_settings, USE_AZURE=True)
class TestAzureRefreshToken(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.client_app = ThirdPartyApplication.objects.create(
            name='Test Client 1',
            client_id='client1',
            origin='http://client1.com'
        )
        self.user_1 = UserModel.objects.create(
            first_name='Test 1',
            email='test.1@example.com',
            username='test.1@example.com',
            is_active=True
        )
        self.user_2 = UserModel.objects.create(
            first_name='Test 2',
            email='test.2@example.com',
            username='test.2@example.com',
            is_active=False
        )
        session_1 = SessionStore()
        session_1['_auth_user_id'] = self.user_1.id
        session_1['third_party_granted_access'] = self.client_app.client_id
        # generate token_cache
        client_id = settings.AZURE_AUTH['CLIENT_ID']
        id_token = build_id_token(
            oid="object1234", preferred_username="John Doe", aud=client_id)
        token_cache = msal.SerializableTokenCache()
        token_cache.add(
            {
                "client_id": client_id,
                "scope": ["s2", "s1", "s3"],  # Not in particular order
                "token_endpoint": "https://login.example.com/contoso/v2/token",
                "response": build_response(
                    uid="uid", utid="utid",  # client_info
                    expires_in=3600, access_token="an access token",
                    id_token=id_token, refresh_token="a refresh token"),
            },
            now=1000
        )
        session_1[f'token_cache_{client_id}'] = token_cache.serialize()
        session_1.create()
        self.session_key_1 = session_1.session_key
        session_2 = SessionStore()
        session_2['_auth_user_id'] = self.user_2.id
        session_2.create()
        self.session_key_2 = session_2.session_key

    def test_get_session(self):
        self.assertTrue(AzureRefreshToken.get_session(self.session_key_1))
        self.assertFalse(AzureRefreshToken.get_session('random'))

    def test_verify_session_user(self):
        session = AzureRefreshToken.get_session(self.session_key_1)
        session_dict = session.get_decoded()
        self.assertTrue(AzureRefreshToken.verify_session_user(
            self.user_1.email,
            session_dict
        ))
        self.assertFalse(AzureRefreshToken.verify_session_user(
            'invalid_email@example.com',
            session_dict
        ))
        session = AzureRefreshToken.get_session(self.session_key_2)
        session_dict = session.get_decoded()
        # inactive user
        self.assertFalse(AzureRefreshToken.verify_session_user(
            self.user_2.email,
            session_dict
        ))
        # create session without auth user
        session_test = SessionStore()
        session_test.create()
        session = AzureRefreshToken.get_session(session_test.session_key)
        session_dict = session.get_decoded()
        self.assertFalse(AzureRefreshToken.verify_session_user(
            self.user_1.email,
            session_dict
        ))

    def test_verify_client_app(self):
        session = AzureRefreshToken.get_session(self.session_key_1)
        session_dict = session.get_decoded()
        self.assertTrue(AzureRefreshToken.verify_client_app(
            self.client_app,
            session_dict
        ))
        # use different client app
        test_app = ThirdPartyApplication.objects.create(
            name='Test Client 2',
            client_id='Client2',
            origin='http://client2.com'
        )
        self.assertFalse(AzureRefreshToken.verify_client_app(
            test_app,
            session_dict
        ))
        session = AzureRefreshToken.get_session(self.session_key_2)
        session_dict = session.get_decoded()
        self.assertFalse(AzureRefreshToken.verify_client_app(
            self.client_app,
            session_dict
        ))

    @mock.patch(
        'azure_auth.handlers.AzureAuthConfig', mocked_azure_config
    )
    @mock.patch(
        'azure_auth.api_views.AzureAuthTokenHandler.'
        'get_access_token_from_cache'
    )
    def test_post_refresh_token(self, mocked_token):
        mocked_token.return_value = None
        view = AzureRefreshToken.as_view()
        request = self.factory.post(
            '/azure-auth/token', {
                'client_id': self.client_app.client_id,
                'email': self.user_1.email,
                'session': self.session_key_1
            }
        )
        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn('refresh token', response.data['detail'])
        mocked_token.return_value = 'this-is-new-access-token'
        view = AzureRefreshToken.as_view()
        request = self.factory.post(
            '/azure-auth/token', {
                'client_id': self.client_app.client_id,
                'email': self.user_1.email,
                'session': self.session_key_1
            }
        )
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertEqual(response.data['access_token'],
                         'this-is-new-access-token')
