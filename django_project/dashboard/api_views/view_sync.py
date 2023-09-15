import math

from django.core.paginator import Paginator
from django.db.models.expressions import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.serializers.view import (
    DatasetViewSyncSerializer,
    DatasetViewResourceSyncSerializer,
    ViewSyncSerializer
)
from georepo.models import (
    DatasetView, DatasetViewResource
)
from georepo.utils.permission import (
    get_views_for_user
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view
)

from georepo.utils.dataset_view import get_view_resource_from_view
from dashboard.tasks import generate_view_export_data


class ViewSyncList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views sync
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        dataset_id = kwargs.get('dataset_id', None)
        (
            _,
            views_querysets
        ) = get_views_for_user(self.request.user)
        view_ids = [v.id for v in views_querysets]

        if dataset_id:
            views_querysets = DatasetView.objects.filter(
                id__in=view_ids,
                dataset_id=dataset_id
            )

        return Response(
            DatasetViewSyncSerializer(
                views_querysets, many=True
            ).data
        )

class ViewResourcesSyncList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        view_id = kwargs.get('view_id', None)
        (
            user_privacy_levels,
            views_querysets
        ) = get_views_for_user(self.request.user)
        view_ids = [v.id for v in views_querysets]

        try:
            view = DatasetView.objects.get(
                id__in=view_ids,
                id=view_id
            )
        except DatasetView.DoesNotExist:
            return Response([], 404)

        resource_level_for_user = view.get_resource_level_for_user(
            user_privacy_levels[int(view_id)]
        )
        view_resources_qs = view.datasetviewresource_set.filter(
            privacy_level__lte=resource_level_for_user,
            entity_count__gt=0
        ).order_by('-privacy_level')

        return Response(
            DatasetViewResourceSyncSerializer(
                view_resources_qs, many=True
            ).data
        )


class SynchronizeView(AzureAuthRequiredMixin, APIView):

    def post(self, *args, **kwargs):
        serializer = ViewSyncSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        view_ids = serializer.validated_data['view_ids']
        views = DatasetView.objects.filter(id__in=view_ids)
        sync_options = serializer.validated_data['sync_options']

        # create tiling_config
        if 'tiling_config' in sync_options:
            for view in views:
                view.match_tiling_config()
        # if sync both vector_tiles and products
        elif len({'vector_tiles', 'products'} - sync_options) == 0:
            for view in views:
                trigger_generate_vector_tile_for_view(
                    view,
                    export_data=True
                )
        # if sync only vector tiles
        elif 'vector_tiles' in sync_options:
            for view in views:
                trigger_generate_vector_tile_for_view(
                    view,
                    export_data=False
                )
        elif 'products' in sync_options:
            for view in views:
                task = generate_view_export_data.delay(view.id)
                view.task_id = task.id
                view.save()

        return Response({})
