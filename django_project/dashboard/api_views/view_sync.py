import math
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from celery.result import AsyncResult
from core.celery import app
from django.db.models.expressions import Q
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.serializers.view import (
    DatasetViewSyncSerializer,
    DatasetViewResourceSyncSerializer,
    ViewSyncSerializer
)
from dashboard.tasks import (
    generate_view_export_data,
    view_simplification_task
)
from georepo.models import (
    Dataset,
    DatasetView, DatasetViewResource,
    DatasetViewTilingConfig
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view
)
from georepo.utils.permission import (
    get_views_for_user
)
from georepo.utils.uuid_helper import is_valid_uuid
from georepo.utils.celery_helper import cancel_task


class ViewSyncList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views sync
    """
    permission_classes = [IsAuthenticated]

    def _filter_sync_status(self, request):
        sync_status_options = dict(request.data).get('sync_status', [])
        if not sync_status_options:
            return Q()

        filters = Q()

        if 'Tiling config does not match dataset' in sync_status_options:
            filters |= Q(
                is_tiling_config_match=False
            )
        if 'Vector tiles not up to date' in sync_status_options:
            filters |= Q(
                vector_tile_sync_status=DatasetView.SyncStatus.OUT_OF_SYNC
            )
        if 'Data products not up to date' in sync_status_options:
            filters |= Q(
                product_sync_status=DatasetView.SyncStatus.OUT_OF_SYNC
            )
        if 'Syncing' in sync_status_options:
            filters |= Q(
                Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCING) |
                Q(product_sync_status=DatasetView.SyncStatus.SYNCING)
            )
        if 'Synced' in sync_status_options:
            filters |= Q(
                Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCED) &
                Q(product_sync_status=DatasetView.SyncStatus.SYNCED)
            )

        return filters

    def _filter_dataset(self, request):
        dataset = dict(request.data).get('dataset', [])
        dataset_ids = dict(request.data).get('dataset', [])
        dataset_ids = [
            int(ds_id) for ds_id in dataset_ids if ds_id.isnumeric()
        ]
        dataset_uuids = [
            ds_uuid for ds_uuid in dataset if is_valid_uuid(ds_uuid, 4)
        ]
        if not dataset:
            return Q()

        return Q(
            Q(dataset__label__in=dataset) |
            Q(dataset_id__in=dataset_ids) |
            Q(dataset__uuid__in=dataset_uuids)
        )

    def _filter_queryset(self, queryset, request):
        dataset_filter = self._filter_dataset(request)
        sync_status_filter = self._filter_sync_status(request)
        args = Q()
        args &= dataset_filter
        args &= sync_status_filter
        return queryset.filter(*(args,))

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        char_fields = [
            field.name for field in DatasetView.get_fields() if
            field.get_internal_type() in
            ['UUIDField', 'CharField', 'TextField']
        ]
        char_fields.extend([
            'dataset__label'
        ])
        q_args = [
            Q(**{f"{field}__icontains": search_text}) for field in char_fields
        ]
        args = Q()
        for arg in q_args:
            args |= arg
        queryset = queryset.filter(*(args,))
        return queryset

    def _sort_queryset(self, queryset, request):
        sort_by = request.query_params.get('sort_by', 'name')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        if not sort_by:
            sort_by = 'name'
        if not sort_direction:
            sort_direction = 'asc'

        ordering_mapping = {
            'dataset': 'dataset__label'
        }
        sort_by = ordering_mapping.get(sort_by, sort_by)
        ordering = sort_by if sort_direction == 'asc' else f"-{sort_by}"
        queryset = queryset.order_by(ordering)
        return queryset

    def post(self, *args, **kwargs):
        dataset_id = kwargs.get('dataset_id', None)
        (
            _,
            views_querysets
        ) = get_views_for_user(self.request.user)
        view_ids = [v.id for v in views_querysets]

        filter_kwargs = {
            'id__in': view_ids
        }

        if dataset_id:
            filter_kwargs['dataset_id'] = dataset_id

        views_querysets = DatasetView.objects.filter(**filter_kwargs)
        views_querysets = self._search_queryset(views_querysets, self.request)
        views_querysets = self._filter_queryset(views_querysets, self.request)
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.query_params.get('page_size', '10'))
        views_querysets = self._sort_queryset(views_querysets, self.request)
        paginator = Paginator(views_querysets, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = DatasetViewSyncSerializer(
                paginated_entities,
                many=True,
                context={
                    'user': self.request.user,
                }
            ).data

        return Response({
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output,
        })


class ViewSyncFilterValue(
    AzureAuthRequiredMixin,
    APIView
):
    """
    Get filter value for given View Sync and criteria
    """
    permission_classes = [IsAuthenticated]
    views_querysets = DatasetView.objects.none()

    def get_user_views(self):
        _, views_querysets = get_views_for_user(self.request.user)
        views_querysets = DatasetView.objects.filter(
            id__in=[v.id for v in views_querysets]
        )
        return views_querysets

    def fetch_dataset(self):
        return list(self.views_querysets.exclude(
            dataset__label__isnull=True
        ).exclude(
            dataset__label__exact=''
        ).order_by().values_list('dataset__label', flat=True).distinct())

    def fetch_tiling_config_not_match(self):
        return [
            'Yes',
            'No'
        ]

    def fetch_vector_tiles_not_updated(self):
        return [
            'Yes',
            'No'
        ]

    def fetch_data_product_not_updated(self):
        return [
            'Yes',
            'No'
        ]


    def fetch_sync_status(self):
        return [
            'Tiling config does not match dataset',
            'Vector tiles not up to date',
            'Data products not up to date',
            'Syncing',
            'Synced'
        ]

    def get(self, request, criteria, *args, **kwargs):
        self.views_querysets = self.get_user_views()
        try:
            data = eval(f"self.fetch_{criteria}()")
        except AttributeError:
            data = []
        return Response(status=200, data=data)


class ViewResourcesSyncList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, view_id, **kwargs):
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
            user_privacy_levels[int(view.dataset_id)]
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
    """
    Synchronize View vector tiles, tiling config, and data.
    """

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
        if len({'vector_tiles', 'products'}.difference(
            set(sync_options))
        ) == 0:
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
                view.product_sync_status = DatasetView.SyncStatus.SYNCING
                view.save(
                    update_fields=['product_sync_status']
                )
                view_resources = DatasetViewResource.objects.filter(
                    dataset_view=view
                )
                for view_resource in view_resources:
                    if view_resource.product_task_id:
                        res = AsyncResult(view_resource.product_task_id)
                        if not res.ready():
                            # find if there is running task and stop it
                            app.control.revoke(
                                view_resource.product_task_id,
                                terminate=True,
                                signal='SIGKILL'
                            )
                    view_resource.status = (
                        DatasetView.DatasetViewStatus.PENDING
                    )
                    view_resource.geojson_progress = 0
                    view_resource.shapefile_progress = 0
                    view_resource.kml_progress = 0
                    view_resource.topojson_progress = 0
                    view_resource.geojson_sync_status = (
                        DatasetView.SyncStatus.SYNCING
                    )
                    view_resource.shapefile_sync_status = (
                        DatasetView.SyncStatus.SYNCING
                    )
                    view_resource.kml_sync_status = (
                        DatasetView.SyncStatus.SYNCING
                    )
                    view_resource.topojson_sync_status = (
                        DatasetView.SyncStatus.SYNCING
                    )
                    view_resource.save(update_fields=[
                        'status', 'geojson_progress', 'shapefile_progress',
                        'kml_progress', 'topojson_progress',
                        'shapefile_sync_status', 'kml_sync_status',
                        'topojson_sync_status', 'geojson_sync_status'
                    ])
                    task = generate_view_export_data.delay(
                        view_resource.id)
                    view_resource.product_task_id = task.id
                    view_resource.save(update_fields=['product_task_id'])
        elif 'simplify' in sync_options:
            for view in views:
                # check if view has custom tiling config
                has_view_tile_configs = (
                    DatasetViewTilingConfig.objects.filter(
                        dataset_view=view
                    ).exists()
                )
                if has_view_tile_configs:
                    if view.simplification_task_id:
                        cancel_task(view.simplification_task_id)
                elif view.dataset.simplification_task_id:
                    cancel_task(view.dataset.simplification_task_id)
                task = view_simplification_task.delay(view.id)
                if has_view_tile_configs:
                    view.simplification_task_id = task.id
                    view.save(update_fields=['simplification_task_id'])
                else:
                    view.dataset.simplification_task_id = task.id
                    view.dataset.save(
                        update_fields=['simplification_task_id'])
        return Response({'status': 'OK'})


class FetchSyncStatus(AzureAuthRequiredMixin, APIView):
    """
    Fetch sync status of view/dataset.
    """
    permission_classes = [IsAuthenticated]

    def get_simplification_status(self, sync_status, simplification_progress):
        status = sync_status
        progress = (
            round(simplification_progress, 2) if
            simplification_progress is not None else 0
        )
        return status, progress

    def get_dataset_status(self, obj: Dataset):
        vt_sync_status = set(
            obj.datasetview_set.all().values_list(
                'vector_tile_sync_status',
                flat=True
            ).distinct()
        )
        product_sync_status = set(
            obj.datasetview_set.all().values_list(
                'product_sync_status',
                flat=True
            ).distinct()
        )
        all_status = vt_sync_status.union(product_sync_status)
        if all_status == {obj.SyncStatus.SYNCED}:
            return obj.SyncStatus.SYNCED
        elif obj.SyncStatus.SYNCING in all_status:
            return obj.SyncStatus.SYNCING
        elif obj.SyncStatus.OUT_OF_SYNC in all_status:
            return obj.SyncStatus.OUT_OF_SYNC
        return obj.SyncStatus.SYNCED

    def get_view_status(self, obj: DatasetView):
        all_status = [
            obj.vector_tile_sync_status,
        ]
        if obj.product_sync_status not in all_status:
            all_status.append(obj.product_sync_status)
        if all_status == [obj.SyncStatus.SYNCED]:
            return obj.SyncStatus.SYNCED
        elif obj.SyncStatus.SYNCING in all_status:
            return obj.SyncStatus.SYNCING
        elif obj.SyncStatus.OUT_OF_SYNC in all_status:
            return obj.SyncStatus.OUT_OF_SYNC
        return obj.SyncStatus.SYNCED

    def get(self, request, *args, **kwargs):
        object_type = kwargs.get('object_type')
        object_uuid = kwargs.get('uuid')
        sync_status = ''

        if object_type == 'dataset':
            dataset = get_object_or_404(
                Dataset,
                uuid=object_uuid
            )
            object_id = dataset.id
            simplification_status, simplification_progress = (
                self.get_simplification_status(
                    dataset.simplification_sync_status,
                    dataset.simplification_progress_num)
            )
            module = dataset.module.name
            sync_status = self.get_dataset_status(dataset)
        elif object_type == 'datasetview':
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=object_uuid
            )
            module = dataset_view.dataset.module.name
            object_id = dataset_view.id
            has_custom_tiling_config = (
                dataset_view.datasetviewtilingconfig_set.all().exists()
            )
            if has_custom_tiling_config:
                simplification_status, simplification_progress = (
                    self.get_simplification_status(
                        dataset_view.simplification_sync_status,
                        dataset_view.simplification_progress_num)
                )
            else:
                simplification_status, simplification_progress = (
                    self.get_simplification_status(
                        dataset_view.dataset.simplification_sync_status,
                        dataset_view.dataset.simplification_progress_num)
                )
            sync_status = self.get_view_status(dataset_view)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return Response(
            status=200,
            data={
                'module': module,
                'object_type': object_type,
                'object_id': object_id,
                'simplification': {
                    'status': simplification_status,
                    'progress': simplification_progress
                },
                'sync_status': sync_status
            }
        )
