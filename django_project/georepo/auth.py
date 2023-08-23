import jwt
from rest_framework import authentication
from django.utils.translation import gettext_lazy as _
from core.models.token_detail import CustomApiKey


class CustomTokenAuthentication(authentication.TokenAuthentication):
    """
    Customized token based authentication.
    Clients should authenticate by passing the token key in the url.
    For example:
        &token={token_key}
    """

    def test_jwt_token(self, token):
        try:
            jwt.get_unverified_header(token)
            return True
        except Exception:
            pass
        return False

    def authenticate_credentials(self, key):
        user, token = (
            super(CustomTokenAuthentication, self).
            authenticate_credentials(key)
        )
        # check flag in TokenDetail
        try:
            if not token.customapikey.is_active:
                raise authentication.exceptions.\
                    AuthenticationFailed(_('Invalid token.'))
        except CustomApiKey.DoesNotExist:
            raise authentication.exceptions.\
                AuthenticationFailed(_('Invalid token.'))
        return (user, token)

    def authenticate(self, request):
        token = request.GET.get('token', '')
        if token:
            keyword = 'Token'
            if self.test_jwt_token(token):
                keyword = 'Bearer'
            request.META['HTTP_AUTHORIZATION'] = f'{keyword} {token}'
        return super(CustomTokenAuthentication, self).authenticate(request)


class BearerAuthentication(CustomTokenAuthentication):
    """
    Simple token based authentication using utvsapitoken.
    Clients should authenticate by passing the token key in the 'Authorization'
    HTTP header, prepended with the string 'Bearer ' or 'Token '.
    """
    keyword = ['token', 'bearer']

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].lower().decode() not in self.keyword:
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise authentication.exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. '
                    'Token string should not contain spaces.')
            raise authentication.exceptions.AuthenticationFailed(msg)
        # skip this authentication if this is a jwt token
        if self.test_jwt_token(auth[1].decode()):
            return None
        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. '
                    'Token string should not contain invalid characters.')
            raise authentication.TokenAuthentication.\
                exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(token)

    def authenticate_header(self, request):
        return self.keyword[0]
