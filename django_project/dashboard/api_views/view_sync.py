import math
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
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
from georepo.tasks.dataset_view import (
    do_patch_centroid_files_for_view
)
from dashboard.tasks import (
    view_simplification_task
)
from georepo.models import (
    Dataset,
    DatasetView, DatasetViewTilingConfig,
    DatasetViewResource
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view
)
from georepo.utils.permission import (
    get_views_for_user
)
from georepo.utils.uuid_helper import is_valid_uuid
from georepo.utils.celery_helper import cancel_task


MAPPED_SYNC_STATUS = {
    'Out of Sync': DatasetView.SyncStatus.OUT_OF_SYNC,
    'Syncing': DatasetView.SyncStatus.SYNCING,
    'Terminated unexpectedly': DatasetView.SyncStatus.ERROR,
    'Done': DatasetView.SyncStatus.SYNCED,
}


def convert_sync_status_filter_value(status_list):
    mapped_status = []
    for status in status_list:
        if status in MAPPED_SYNC_STATUS:
            mapped_status.append(MAPPED_SYNC_STATUS[status])
    return mapped_status


def trigger_sync_centroid_file(view: DatasetView):
    resources = DatasetViewResource.objects.filter(
        dataset_view=view,
        entity_count__gt=0
    ).order_by('id')
    for resource in resources:
        resource.centroid_sync_status = DatasetViewResource.SyncStatus.SYNCING
        resource.save(update_fields=['centroid_sync_status'])
    do_patch_centroid_files_for_view.delay(view.id)


class ViewSyncList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views sync
    """
    permission_classes = [IsAuthenticated]

    def _filter_sync_status(self, request):
        sync_status = request.data.get('vector_tile_sync_status', [])
        tiling_config_status = request.data.get('is_tiling_config_match', [])
        simplification_status = request.data.get('simplification_status', [])
        centroid_sync_status = request.data.get('centroid_sync_status', [])
        filters = Q()
        if sync_status:
            filters |= Q(
                vector_tile_sync_status__in=convert_sync_status_filter_value(
                    sync_status)
            )
        if centroid_sync_status:
            filters |= Q(
                centroid_sync_status__in=convert_sync_status_filter_value(
                    centroid_sync_status)
            )
        if tiling_config_status:
            tiling_filter = (
                tiling_config_status[0] == 'Tiling config matches dataset'
            )
            filters |= Q(
                is_tiling_config_match=tiling_filter
            )
        if simplification_status:
            status_list = convert_sync_status_filter_value(
                simplification_status)
            filters |= Q(
                Q(is_tiling_config_match=True) &
                Q(dataset__simplification_sync_status__in=status_list)
            )
            filters |= Q(
                Q(is_tiling_config_match=False) &
                Q(simplification_sync_status__in=status_list)
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
        sync_status_filter = self._filter_sync_status(request)
        return queryset.filter(sync_status_filter)

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        char_fields = [
            field.name for field in DatasetView.get_fields() if
            field.get_internal_type() in
            ['UUIDField', 'CharField', 'TextField']
        ]
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
            'name': 'name'
        }
        sort_by = ordering_mapping.get(sort_by, sort_by)
        ordering = sort_by if sort_direction == 'asc' else f"-{sort_by}"
        queryset = queryset.order_by(ordering)
        return queryset

    def _select_all_queryset(self, views_querysets):
        # exclude synced and syncing
        querysets = views_querysets.exclude(
            Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCING) |
            Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCED)
        )
        querysets = querysets.values_list('id', flat=True)
        return querysets

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
        # get count select all rows
        select_all_qs = self._select_all_queryset(views_querysets)
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
            'total_selectable_rows': select_all_qs.count()
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
        if len({'vector_tiles', 'centroid'}.difference(
            set(sync_options))
        ) == 0:
            for view in views:
                trigger_generate_vector_tile_for_view(
                    view
                )
                trigger_sync_centroid_file(view)
        # if sync only vector tiles
        elif 'vector_tiles' in sync_options:
            for view in views:
                trigger_generate_vector_tile_for_view(
                    view
                )
        elif 'centroid' in sync_options:
            for view in views:
                trigger_sync_centroid_file(view)
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
        all_status = set(
            obj.datasetview_set.all().values_list(
                'vector_tile_sync_status',
                flat=True
            ).distinct()
        )
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


class ViewSyncSelectAllList(ViewSyncList):
    """
    API to fetch list of Id for select All
    """
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
        select_all_qs = self._select_all_queryset(views_querysets)
        return Response(status=200, data=select_all_qs)
