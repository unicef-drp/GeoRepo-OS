import os
from django.conf import settings
from drf_yasg import openapi


def get_api_pagination_parameters():
    if settings.DEBUG or 'test' in os.environ['DJANGO_SETTINGS_MODULE']:
        return {
            'minimum': 1,
            'maximum': 50,
            'default': 50
        }
    from core.models.preferences import SitePreferences
    try:
        preferences = SitePreferences.preferences()
    except Exception:
        preferences = SitePreferences()
    return {
        'minimum': 1,
        'maximum': preferences.api_config['max_page_size'],
        'default': preferences.api_config['default_page_size']
    }


api_pagination_params = get_api_pagination_parameters()


common_api_params = [
    openapi.Parameter(
        'page', openapi.IN_QUERY,
        description='Page number in pagination',
        type=openapi.TYPE_INTEGER,
        default=1
    ), openapi.Parameter(
        'page_size', openapi.IN_QUERY,
        description='Total records in a page',
        type=openapi.TYPE_INTEGER,
        **api_pagination_params
    )
]
