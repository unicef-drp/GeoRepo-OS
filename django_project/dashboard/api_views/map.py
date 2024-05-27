import ast
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.api_views.common import (
    DatasetReadPermission
)
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView, DatasetViewResource
from dashboard.api_views.views import DatasetViewReadPermission
from georepo.utils.dataset_view import (
    get_view_resource_from_view
)
from georepo.utils.permission import (
    get_view_permission_privacy_level
)


def get_bbox_from_view_resource(resource: DatasetViewResource):
    bbox = []
    if resource is None:
        return bbox
    if resource.bbox:
        bbox_str = '[' + resource.bbox + ']'
        bbox = ast.literal_eval(bbox_str)
    return bbox


class DatasetBbox(AzureAuthRequiredMixin, DatasetReadPermission, APIView):
    """
    Return dataset bbox
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        uuid = kwargs.get('id')
        dataset = get_object_or_404(Dataset, uuid=uuid)
        privacy_level = get_view_permission_privacy_level(
            self.request.user, dataset)
        # find all version view
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code__isnull=True
        ).first()
        if dataset_view is None:
            return Response(status=200, data=[])
        resource = get_view_resource_from_view(
            dataset_view, privacy_level)
        return Response(status=200,
                        data=get_bbox_from_view_resource(resource))


class ViewBbox(AzureAuthRequiredMixin,
               DatasetViewReadPermission, APIView):
    """
    Return view bbox
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        privacy_level = get_view_permission_privacy_level(
            self.request.user, dataset_view.dataset,
            dataset_view=dataset_view)
        resource = get_view_resource_from_view(
            dataset_view, privacy_level)
        return Response(status=200,
                        data=get_bbox_from_view_resource(resource))
