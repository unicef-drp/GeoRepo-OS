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


search_param = openapi.Parameter(
    'search', openapi.IN_QUERY,
    description='Search query',
    type=openapi.TYPE_STRING
)
search_type_param = openapi.Parameter(
    'search_type', openapi.IN_QUERY,
    description='Search query type: name or ucode',
    type=openapi.TYPE_STRING
)


sort_param = openapi.Parameter(
    'sort', openapi.IN_QUERY,
    description='Sort parameter',
    type=openapi.TYPE_STRING
)


class APISortBase:
    """Base class to sort queryset."""

    sort_attribute_mapping = {}
    default_sort = []

    def _sort_default(self, queryset):
        if self.default_sort:
            return queryset.order_by(*self.default_sort)
        return queryset

    def sort_queryset(self, request, queryset):
        """Sort queryset based on request parameter."""
        sort = request.GET.get('sort', None)
        if not sort:
            return self._sort_default(queryset)

        if len(self.sort_attribute_mapping.keys()) == 0:
            return self._sort_default(queryset)

        sort_keywords = []
        raws = sort.split(',')
        for raw in raws:
            is_desc = raw.startswith('-')
            cleaned_raw = raw.replace('-', '')
            if cleaned_raw not in self.sort_attribute_mapping:
                continue
            sort_keywords.append(
                f'-{self.sort_attribute_mapping[cleaned_raw]}' if is_desc else
                self.sort_attribute_mapping[cleaned_raw]
            )

        if not sort_keywords:
            return self._sort_default(queryset)

        return queryset.order_by(*sort_keywords)
