from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseForbidden
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.api_views.views import DatasetViewReadPermission
from georepo.models.export_request import (
    ExportRequest
)
from dashboard.models.entities_user_config import EntitiesUserConfig


class ExportHistoryList(AzureAuthRequiredMixin,
                        DatasetViewReadPermission, APIView):
    """
    API to fetch list of export request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()


class ExportRequestDetail(AzureAuthRequiredMixin,
                          DatasetViewReadPermission, APIView):
    """
    API to create and fetch export request detail.
    """

    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        request_id = self.request.GET.get('request_id')

    def post(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()


class ExportRequestMetadata(AzureAuthRequiredMixin,
                            DatasetViewReadPermission, APIView):
    """
    API to fetch metadat for requesting export data.
    """

    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        # EntitiesUserConfig session
        session_id = self.request.GET.get('session_id')
        return Response(status=200)

