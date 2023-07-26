from django.urls import path, re_path

from georepo.views.layer_test import LayerTestView
from georepo.api_views.protected_api import IsDatasetAllowedAPI

urlpatterns = [
    path('layer-test/', LayerTestView.as_view()),
    re_path(
        r'api/protected/?$',
        IsDatasetAllowedAPI.as_view(),
        name='dataset-allowed-api'
    )
]
