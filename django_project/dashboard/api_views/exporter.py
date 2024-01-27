from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.api_views.views import DatasetViewReadPermission
from georepo.models.dataset_view import DatasetView
from georepo.models.base_task_request import PENDING
from georepo.models.export_request import (
    ExportRequest,
    AVAILABLE_EXPORT_FORMAT_TYPES,
    ExportRequestStatusText
)
from dashboard.models.entities_user_config import EntitiesUserConfig
from dashboard.api_views.tiling_config import FetchDatasetViewTilingConfig
from dashboard.serializers.export_request import (
    ExportRequestItemSerializer,
    ExportRequestDetailSerializer
)
from georepo.models.dataset_tile_config import DatasetTilingConfig
from georepo.models.dataset_view_tile_config import DatasetViewTilingConfig
from georepo.tasks.dataset_view import dataset_view_exporter


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
        return Response(
            status=200,
            data=ExportRequestItemSerializer(export_requests, many=True).data
        )


class ExportRequestDetail(AzureAuthRequiredMixin,
                          DatasetViewReadPermission, APIView):
    """
    API to create and fetch export request detail.
    """

    def check_zoom_level(self, dataset_view: DatasetView, zoom_level: int):
        if dataset_view.is_tiling_config_match:
            return DatasetTilingConfig.objects.filter(
                dataset=dataset_view.dataset,
                zoom_level=zoom_level
            ).exists()
        return DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view,
            zoom_level=zoom_level
        )

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
        # validate format
        if format not in AVAILABLE_EXPORT_FORMAT_TYPES:
            return Response(
                status=400,
                data={
                    'detail': f'Invalid format type: {format}'
                }
            )
        # validate zoom level
        if is_simplified_entities:
            if not dataset_view.is_simplified_entities_ready:
                return Response(
                    status=400,
                    data={
                        'detail': (
                            'There is ongoing simplification process'
                            ' for the view!' if
                            dataset_view.current_simplification_status ==
                            'syncing' else
                            'The view has out of sync simplified entities!'
                        )
                    }
                )
            if (
                not self.check_zoom_level(dataset_view,
                                          simplification_zoom_level)
            ):
                return Response(
                    status=400,
                    data={
                        'detail': (
                            'Invalid simplification '
                            f'zoom level {simplification_zoom_level}'
                        )
                    }
                )
        # validate correct format
        export_request = ExportRequest.objects.create(
            dataset_view=dataset_view,
            format=format,
            submitted_on=timezone.now(),
            submitted_by=self.request.user,
            status=PENDING,
            status_text=str(ExportRequestStatusText.WAITING),
            is_simplified_entities=is_simplified_entities,
            simplification_zoom_level=simplification_zoom_level,
            filters=filters
        )
        celery_task = dataset_view_exporter.apply_async(
            (export_request.id,), queue='exporter'
        )
        export_request.task_id = celery_task.id
        export_request.save(update_fields=['task_id'])
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
        session = self.request.GET.get('session')
        user_config = EntitiesUserConfig.objects.filter(
            uuid=session
        ).first()
        return Response(
            status=200,
            data={
                'filters': user_config.filters if user_config else {},
                'available_formats': AVAILABLE_EXPORT_FORMAT_TYPES.sort(),
                'is_simplification_available': (
                    dataset_view.is_simplified_entities_ready
                ),
                'tiling_configs': self.fetch_view_tiling_configs(dataset_view)
            }
        )
