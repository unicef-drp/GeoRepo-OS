# -*- coding: utf-8 -*-
"""Django settings for georepo project."""

import os
from .utils import absolute_path, ensure_secret_key_file
ensure_secret_key_file()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = '/home/web/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = '/home/web/static'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    absolute_path('core', 'static'),
    absolute_path('dashboard', 'bundles'),
)

# Every cache key will get prefixed with this value - here we set it to
# the name of the directory the project is in to try and use something
# project specific.
CACHE_MIDDLEWARE_KEY_PREFIX = 'georepo'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'core.middleware.VersionMiddleware'
]

ROOT_URLCONF = 'core.urls'
GRAPPELLI_ADMIN_TITLE = ''

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'core.wsgi.application'

# import SECRET_KEY into current namespace
# noinspection PyUnresolvedReferences
from .secret import SECRET_KEY  # noqa

# New django 1.8 templates settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Put Templates Hers
            absolute_path('core', 'templates'),
            absolute_path('dashboard', 'templates'),
            absolute_path('georepo', 'templates'),
        ],
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.global_context.global_context',
                'django.template.context_processors.request'
            ],
        },
    },
]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

INSTALLED_APPS = (
    'function_patch',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.redirects',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.gis',
    'django.contrib.messages',
    'core.staticfiles_config.MyStaticFilesConfig',
)

SITE_ID = 1
STATICFILES_STORAGE = (
    'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': (
            f'redis://default:{os.environ.get("REDIS_PASSWORD", "")}'
            f'@{os.environ.get("REDIS_HOST", "")}',
        )
    }
}

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/'
LAYER_TILES_PATH = os.getenv('LAYER_TILES_PATH')
LAYER_TILES_BASE_URL = os.getenv(
    'LAYER_TILES_BASE_URL', 'http://0.0.0.0:51101')

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240  # higher than the count of fields

# swagger UI settings
SWAGGER_SETTINGS = {
    'TAGS_SORTER': 'alpha',
    'showCommonExtensions': 'true',
    'SECURITY_DEFINITIONS': {
        'ApiKey Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    }
}
