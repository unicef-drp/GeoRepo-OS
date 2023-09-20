# coding=utf-8
"""Main django urls."""
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator

from django.conf import settings
from django.urls import re_path, include, path
from django.views.generic.base import RedirectView
from django.contrib.auth.views import LoginView
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseNotFound
import json


class CustomSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ['https']
        if settings.DEBUG:
            schema.schemes = ['http'] + schema.schemes
        return schema


class CustomLoginView(LoginView):
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        next = self.request.GET.get('next', '')
        context = super().get_context_data(**kwargs)
        context['logged_out'] = self.request.GET.get('logged_out', False)
        context['no_access'] = self.request.GET.get('no_access', False)
        context['use_azure_auth'] = settings.USE_AZURE
        context['redirect_next_uri'] = next
        return context


schema_view_v1 = get_schema_view(
    openapi.Info(
        title="GeoRepo API",
        default_version='v1.0.0'
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    generator_class=CustomSchemaGenerator,
    patterns=[
        re_path(r'api/v1/', include(
            ('georepo.urls_v1', 'api'),
            namespace='v1')
        )
    ],
)

admin.autodiscover()

urlpatterns = [
    re_path(r'^api/v1/docs/$', schema_view_v1.with_ui(
                'swagger', cache_timeout=0),
            name='schema-swagger-ui'),
    re_path(
        r'^admin/core/sitepreferences/$',
        RedirectView.as_view(
            url='/admin/core/sitepreferences/1/change/',
            permanent=False
        ),
        name='site-preferences'
    ),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^watchman/', include('watchman.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)

if settings.USE_AZURE:
    # azure auth
    urlpatterns += [
        re_path(r"^login[/]?", CustomLoginView.as_view(), name="login"),
        path("", include("azure_auth.urls",
                         namespace="azure_auth"))
    ]
else:
    urlpatterns += [
        path('account/', include('django.contrib.auth.urls')),
    ]

# django simple captcha URLs
urlpatterns += [
    path('captcha/', include('captcha.urls')),
]

urlpatterns += [
    re_path(r'^api/v1/', include(('georepo.urls_v1', 'api'), namespace='v1')),
    re_path(r'^(?!api/v1/)', include('georepo.urls')),
    re_path(r'^(?!api/v1/)', include('docs.urls')),
    re_path(r'^(?!api/v1/)', include('dashboard.urls')),
]


def response404(request, exception):
    # handler when no url is found
    data = {'detail': 'Not Found'}
    return HttpResponseNotFound(
        json.dumps(data),
        content_type='application/json'
    )


handler404 = response404  # noqa
