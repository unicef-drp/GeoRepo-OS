from .dev import *  # noqa

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

AZURE_AUTH = {}
USE_AZURE = False
AUTHENTICATION_BACKENDS = [x for x in AUTHENTICATION_BACKENDS if x != 'azure_auth.backends.AzureAuthBackend']
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [x for x in REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] if x != 'azure_auth.backends.JWTAccessTokenAuthentication']
