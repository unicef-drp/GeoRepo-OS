from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from .models import ThirdPartyApplication
from .handlers import AzureAuthTokenHandler

UserModel = get_user_model()


class AzureRefreshToken(APIView):
    """Renew token using refresh token from Azure B2c."""
    permission_classes = [AllowAny]

    @staticmethod
    def get_session(session_key) -> Session:
        session = Session.objects.filter(session_key=session_key).first()
        return session

    @staticmethod
    def verify_session_user(user_email, session_dict):
        auth_user_id = session_dict.get('_auth_user_id', None)
        if auth_user_id is None:
            return False
        return UserModel.objects.filter(
            id=auth_user_id,
            is_active=True,
            email=user_email
        ).exists()

    @staticmethod
    def verify_client_app(app: ThirdPartyApplication, session_dict):
        third_party_client_key = 'third_party_granted_access'
        if third_party_client_key not in session_dict:
            return False
        granted_client_ids = session_dict.get(third_party_client_key, [])
        return app.client_id in granted_client_ids

    def azure_auth_refresh_silent(self, session, session_data):
        token_handler = AzureAuthTokenHandler(session_data)
        access_token = token_handler.get_access_token_from_cache()
        if access_token is None:
            return None
        # save new access and refresh token back to session data
        session_data = token_handler.save_token_cache(session_data)
        session.session_data = Session.objects.encode(session_data)
        session.save()
        return access_token

    def post(self, request, *args, **kwargs):
        client_id = request.data.get('client_id')
        user_email = request.data.get('email')
        session_key = request.data.get('session')
        app = get_object_or_404(
            ThirdPartyApplication,
            client_id=client_id
        )
        session = self.get_session(session_key)
        if session is None:
            return Response(
                status=400,
                data={
                    'detail': 'Invalid session!'
                }
            )
        session_dict = session.get_decoded()
        # validate user session
        if not self.verify_session_user(user_email, session_dict):
            return Response(
                status=400,
                data={
                    'detail': 'Invalid user!'
                }
            )
        # validate client app
        if not self.verify_client_app(app, session_dict):
            return Response(
                status=400,
                data={
                    'detail': 'Invalid client_id!'
                }
            )
        access_token = self.azure_auth_refresh_silent(session, session_dict)
        if access_token:
            return Response(
                status=200,
                data={
                    'access_token': access_token,
                    'client_id': app.client_id
                }
            )
        return Response(
            status=400,
            data={
                'detail': 'Invalid refresh token!'
            }
        )
