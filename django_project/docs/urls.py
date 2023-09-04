from django.urls import re_path
from django.contrib import admin
from django.views.generic.base import RedirectView

from docs.api.documentation import DocumentationDetail

admin.autodiscover()

urlpatterns = [
    re_path(
        r'^django-admin/docs/preferences/$',
        RedirectView.as_view(
            url='/django-admin/docs/preferences/1/change/',
            permanent=False),
        name='index'
    ),
    re_path(
        r'^docs/(?P<page_name>[^/]+)/data',
        DocumentationDetail.as_view(),
        name='documentation-detail'
    )
]
