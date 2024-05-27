from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.api_views.views import DatasetViewReadPermission
from georepo.models.base_task_request import PENDING, PROCESSING
from georepo.models.export_request import (
    ExportRequest,
    AVAILABLE_EXPORT_FORMAT_TYPES
)
from dashboard.models.entities_user_config import EntitiesUserConfig
from dashboard.api_views.tiling_config import FetchDatasetViewTilingConfig
from dashboard.serializers.export_request import (
    ExportRequestItemSerializer,
    ExportRequestDetailSerializer
)
from georepo.api_views.dataset_view import DatasetViewExportBase


class ExportHistoryList(AzureAuthRequiredMixin,
                        DatasetViewReadPermission, APIView):
    """
    API to fetch list of export request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        export_requests = ExportRequest.objects.filter(
            dataset_view=dataset_view
        )
        if not self.request.user.is_superuser:
            export_requests = export_requests.filter(
                submitted_by=self.request.user
            )
        export_requests = export_requests.order_by('-submitted_on')
        is_processing_qs = export_requests.filter(
            status__in=[PENDING, PROCESSING]
        )
        return Response(
            status=200,
            data={
                'results': (
                    ExportRequestItemSerializer(
                        export_requests, many=True).data
                ),
                'is_processing': is_processing_qs.exists()
            }
        )


class ExportRequestDetail(AzureAuthRequiredMixin,
                          DatasetViewReadPermission,
                          DatasetViewExportBase,
                          APIView):
    """
    API to create and fetch export request detail.
    """

    def get(self, *args, **kwargs):
        request_id = self.request.GET.get('request_id')
        export_request = get_object_or_404(ExportRequest, id=request_id)
        return Response(
            status=200,
            data=ExportRequestDetailSerializer(export_request).data
        )

    def post(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        filters = self.request.data.get('filters', {})
        is_simplified_entities = self.request.data.get(
            'is_simplified_entities')
        simplification_zoom_level = self.request.data.get(
            'simplification_zoom_level'
        )
        format = self.request.data.get(
            'format'
        )
        validation_response = self.validate_request(
            dataset_view, format, is_simplified_entities,
            simplification_zoom_level
        )
        if validation_response:
            return validation_response
        export_request = self.submit_export_request(
            dataset_view, format, self.request.user,
            is_simplified_entities, simplification_zoom_level,
            filters, 'dashboard'
        )
        return Response(
            status=201,
            data=ExportRequestDetailSerializer(export_request).data
        )


class ExportRequestMetadata(FetchDatasetViewTilingConfig,
                            DatasetViewReadPermission):
    """
    API to fetch metadata for requesting export data.
    """

    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        # EntitiesUserConfig session
        session = self.request.GET.get('session', '')
        user_config = None
        if session:
            user_config = EntitiesUserConfig.objects.filter(
                uuid=session
            ).first()
        formats = []
        formats.extend(AVAILABLE_EXPORT_FORMAT_TYPES)
        formats.sort()
        return Response(
            status=200,
            data={
                'filters': user_config.filters if user_config else {},
                'available_formats': formats,
                'is_simplification_available': (
                    dataset_view.is_simplified_entities_ready
                ),
                'current_simplification_status': (
                    dataset_view.current_simplification_status
                ),
                'tiling_configs': self.fetch_view_tiling_configs(dataset_view)
            }
        )
