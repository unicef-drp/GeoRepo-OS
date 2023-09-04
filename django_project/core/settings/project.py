# coding=utf-8

"""Project level settings.

Adjust these values as needed but don't commit passwords etc. to any public
repository!
"""

import os  # noqa

from django.utils.translation import gettext_lazy as _

from .contrib import *  # noqa
from .utils import code_release_version

ALLOWED_HOSTS = ['*']
ADMINS = (
    ('Dimas Ciputra', 'dimas@kartoza.com'),
)
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USERNAME'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.environ['DATABASE_HOST'],
        'PORT': 5432,
        'TEST_NAME': 'unittests',
    }
}

# Due to profile page does not available,
# this will redirect to home page after login
LOGIN_REDIRECT_URL = '/'

# How many versions to list in each project box
PROJECT_VERSION_LIST_SIZE = 10

# Set debug to false for production
DEBUG = TEMPLATE_DEBUG = False

SOUTH_TESTS_MIGRATE = False

# Set languages which want to be translated
LANGUAGES = (
    ('en', _('English')),
)

# Set storage path for the translation files
LOCALE_PATHS = (absolute_path('locale'),)

# Extra installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'azure_auth',
    'core',
    'georepo',
    'dashboard',
    'modules',
)

EXPORT_FOLDER_OUTPUT = os.path.join(
    MEDIA_ROOT,
    'export_data'
)

if not os.path.exists(EXPORT_FOLDER_OUTPUT):
    os.mkdir(EXPORT_FOLDER_OUTPUT)

GEOJSON_FOLDER_OUTPUT = os.path.join(
    EXPORT_FOLDER_OUTPUT,
    'geojson'
)

if not os.path.exists(GEOJSON_FOLDER_OUTPUT):
    os.mkdir(GEOJSON_FOLDER_OUTPUT)

SHAPEFILE_FOLDER_OUTPUT = os.path.join(
    EXPORT_FOLDER_OUTPUT,
    'shapefile'
)

if not os.path.exists(SHAPEFILE_FOLDER_OUTPUT):
    os.mkdir(SHAPEFILE_FOLDER_OUTPUT)

KML_FOLDER_OUTPUT = os.path.join(
    EXPORT_FOLDER_OUTPUT,
    'kml'
)

if not os.path.exists(KML_FOLDER_OUTPUT):
    os.mkdir(KML_FOLDER_OUTPUT)

TOPOJSON_FOLDER_OUTPUT = os.path.join(
    EXPORT_FOLDER_OUTPUT,
    'topojson'
)

if not os.path.exists(TOPOJSON_FOLDER_OUTPUT):
    os.mkdir(TOPOJSON_FOLDER_OUTPUT)

# use custom filter to hide other sensitive informations
DEFAULT_EXCEPTION_REPORTER_FILTER = (
    'core.settings.filter.ExtendSafeExceptionReporterFilter'
)

# empty config will be not using azure
AZURE_AUTH = {}
USE_AZURE = False

USE_AZURE = os.environ.get('AZURE_B2C_CLIENT_ID', '') != ''
if USE_AZURE:
    LOGIN_URL = 'login'
    # redirect when user is not within Unicef group and
    # does not have GeoRepo account
    USER_NO_ACCESS_URL = ''
    LOGOUT_REDIRECT_URL = '/login/?logged_out=true'
    AZURE_AUTH = {
        'CLIENT_ID': os.environ.get('AZURE_B2C_CLIENT_ID'),
        'CLIENT_SECRET': os.environ.get('AZURE_B2C_CLIENT_SECRET'),
        'TENANT_NAME': os.environ.get('AZURE_B2C_TENANT_NAME'),
        'POLICY_NAME': os.environ.get('AZURE_B2C_POLICY_NAME'),
        'RENAME_ATTRIBUTES': [
            ('given_name', 'first_name'),
            ('family_name', 'last_name'),
            ('email', 'email')
        ],
        'SAVE_ID_TOKEN_CLAIMS': False,
        # request access token
        'SCOPES': [os.environ.get('AZURE_B2C_CLIENT_ID')],
        'PUBLIC_URLS': [
            'schema-swagger-ui',
            'dataset-allowed-api'
        ],
    }
    AUTHENTICATION_BACKENDS = [
        'azure_auth.backends.AzureAuthBackend'
    ] + AUTHENTICATION_BACKENDS
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
        REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] +
        ['azure_auth.backends.JWTAccessTokenAuthentication']
    )
    # add azure templates
    TEMPLATES[0]['DIRS'] += [
        absolute_path('azure_auth', 'templates')
    ]
    # override logout url in swagger ui
    SWAGGER_SETTINGS['LOGIN_URL'] = '/azure-auth/login'
    SWAGGER_SETTINGS['LOGOUT_URL'] = '/azure-auth/logout'
    SWAGGER_SETTINGS['SECURITY_DEFINITIONS'].update({
        'B2C JWT Token Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    })
    # Azure blob storage
    AZURE_STORAGE = os.environ.get('AZURE_STORAGE')
    AZURE_STORAGE_CONTAINER = os.environ.get('AZURE_STORAGE_CONTAINER')
    # django azure storage settings
    DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
    AZURE_CONNECTION_STRING = AZURE_STORAGE
    AZURE_CONTAINER = AZURE_STORAGE_CONTAINER
    # 100MB
    AZURE_BLOB_MAX_MEMORY_SIZE = 100*1024*1024
    AZURE_OVERWRITE_FILES = True
    AZURE_LOCATION = 'media'
CODE_RELEASE_VERSION = code_release_version()
