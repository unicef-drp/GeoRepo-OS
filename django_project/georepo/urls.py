from django.urls import path, re_path

from georepo.views.layer_test import LayerTestView
from georepo.api_views.protected_api import IsDatasetAllowedAPI
from georepo.api_views.tile import TileAPIView

urlpatterns = [
    path('layer-test/', LayerTestView.as_view()),
    re_path(
        r'api/protected/?$',
        IsDatasetAllowedAPI.as_view(),
        name='dataset-allowed-api'
    ),
    re_path(r'layer_tiles/'
            r'(?P<resource>[\da-f-]+)/'
            r'(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)/?$',
            TileAPIView.as_view(),
            name='download-vector-tile'),
]
