from django.conf import settings
import uuid
from math import isclose
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from azure_auth.backends import AzureAuthRequiredMixin
from celery.result import AsyncResult
from django.utils import timezone
from core.celery import app
from georepo.models import Dataset, DatasetView, DatasetViewResource
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig, TemporaryTilingConfig,
    AdminLevelTilingConfig
)
from georepo.models.dataset_view_tile_config import (
    DatasetViewTilingConfig,
    ViewAdminLevelTilingConfig
)
from dashboard.serializers.tiling_config import (
    TilingConfigSerializer,
    ViewTilingConfigSerializer
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view
)
from georepo.tasks.simplify_geometry import (
    simplify_geometry_in_dataset,
    simplify_geometry_in_view
)
from dashboard.api_views.common import (
    DatasetManagePermission
)


class FetchDatasetTilingConfig(AzureAuthRequiredMixin,
                               DatasetManagePermission, APIView):
    """
    Fetch dataset tiling config
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        tiling_configs = DatasetTilingConfig.objects.filter(
            dataset=dataset
        ).order_by('zoom_level')
        return Response(
            status=200,
            data=TilingConfigSerializer(tiling_configs, many=True).data
        )


class FetchDatasetViewTilingConfig(AzureAuthRequiredMixin, APIView):
    """
    Fetch dataset view tiling config
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_view_uuid = kwargs.get('view')
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        # find from View tiling configs
        view_tiling_configs = DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view
        ).order_by('zoom_level')
        if view_tiling_configs.exists():
            return Response(
                status=200,
                data=ViewTilingConfigSerializer(
                    view_tiling_configs,
                    many=True
                ).data
            )
        tiling_configs = DatasetTilingConfig.objects.filter(
            dataset=dataset_view.dataset
        ).order_by('zoom_level')
        return Response(
            status=200,
            data=TilingConfigSerializer(tiling_configs, many=True).data
        )


class CreateTemporaryTilingConfig(AzureAuthRequiredMixin, APIView):
    """
    Init tiling config update wizard
    """
    permission_classes = [IsAuthenticated]

    def create_temp_tiling_config_for_dataset(self, dataset_uuid):
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        new_session_uuid = str(uuid.uuid4())
        tiling_configs = DatasetTilingConfig.objects.filter(
            dataset=dataset
        ).order_by('zoom_level')
        for tiling_config in tiling_configs:
            level_configs = (
                tiling_config.adminleveltilingconfig_set.all().order_by(
                    'level'
                )
            )
            for level_config in level_configs:
                TemporaryTilingConfig.objects.create(
                    session=new_session_uuid,
                    zoom_level=tiling_config.zoom_level,
                    level=level_config.level,
                    simplify_tolerance=level_config.simplify_tolerance,
                    created_at=timezone.now()
                )
        return new_session_uuid

    def create_temp_tiling_config_for_datasetview(self, dataset_view_uuid):
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        new_session_uuid = str(uuid.uuid4())
        view_tiling_configs = DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view
        ).order_by('zoom_level')
        if not view_tiling_configs.exists():
            return self.create_temp_tiling_config_for_dataset(
                dataset_view.dataset.uuid
            )
        for tiling_config in view_tiling_configs:
            level_configs = (
                tiling_config.viewadminleveltilingconfig_set.all().order_by(
                    'level'
                )
            )
            for level_config in level_configs:
                TemporaryTilingConfig.objects.create(
                    session=new_session_uuid,
                    zoom_level=tiling_config.zoom_level,
                    level=level_config.level,
                    simplify_tolerance=level_config.simplify_tolerance,
                    created_at=timezone.now()
                )
        return new_session_uuid

    def post(self, request, *args, **kwargs):
        object_uuid = request.data.get('object_uuid')
        # dataset or datasetview
        object_type = request.data.get('object_type')
        session = None
        if object_type == 'dataset':
            session = self.create_temp_tiling_config_for_dataset(object_uuid)
        elif object_type == 'datasetview':
            session = (
                self.create_temp_tiling_config_for_datasetview(object_uuid)
            )
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return Response(
            status=201,
            data={
                'session': session
            }
        )


class TemporaryTilingConfigAPIView(AzureAuthRequiredMixin, APIView):
    """
    Fetch and Update temporary tiling config
    """
    permission_classes = [IsAuthenticated]

    def get_tiling_configs_from_session(self, session):
        zoom_levels = TemporaryTilingConfig.objects.filter(
            session=session
        ).order_by('zoom_level').values_list(
            'zoom_level',
            flat=True
        ).distinct()
        data = []
        for zoom_level in zoom_levels:
            configs = TemporaryTilingConfig.objects.filter(
                session=session,
                zoom_level=zoom_level
            ).order_by('zoom_level')
            tiling_configs = [
                {
                    'level': c.level,
                    'simplify_tolerance': c.simplify_tolerance
                } for c in configs
            ]
            data.append({
                'zoom_level': zoom_level,
                'admin_level_tiling_configs': tiling_configs
            })
        return data

    def get(self, request, *args, **kwargs):
        session = kwargs.get('session')
        data = self.get_tiling_configs_from_session(session)
        return Response(
            status=200,
            data=data
        )

    def post(self, request, *args, **kwargs):
        session = kwargs.get('session')
        TemporaryTilingConfig.objects.filter(
            session=session
        ).delete()
        for data in request.data:
            zoom_level = data['zoom_level']
            if zoom_level < 0:
                raise ValidationError(
                    f'Invalid zoom level {zoom_level}'
                )
            for config in data['admin_level_tiling_configs']:
                TemporaryTilingConfig.objects.create(
                    session=session,
                    zoom_level=zoom_level,
                    level=config['level'],
                    simplify_tolerance=config['simplify_tolerance'],
                    created_at=timezone.now()
                )
        return Response(status=204)


class ConfirmTemporaryTilingConfigAPIView(TemporaryTilingConfigAPIView):
    """
    Confirm and apply temporary tiling config
    """
    permission_classes = [IsAuthenticated]

    def apply_to_dataset(self, dataset_uuid, configs):
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        DatasetTilingConfig.objects.filter(
            dataset=dataset
        ).delete()
        for config in configs:
            tiling_config = DatasetTilingConfig.objects.create(
                dataset=dataset,
                zoom_level=config['zoom_level']
            )
            for level_config in config['admin_level_tiling_configs']:
                AdminLevelTilingConfig.objects.create(
                    dataset_tiling_config=tiling_config,
                    level=level_config['level'],
                    simplify_tolerance=level_config['simplify_tolerance']
                )
        # reset dataset styles because zoom could be changed
        dataset.styles = None
        dataset.style_source_name = ''
        dataset.save(update_fields=['styles', 'style_source_name'])
        # Trigger simplification
        if dataset.simplification_task_id:
            res = AsyncResult(dataset.simplification_task_id)
            if not res.ready():
                app.control.revoke(
                    dataset.simplification_task_id,
                    terminate=True
                )
        task_simplify = simplify_geometry_in_dataset.delay(dataset.id)
        dataset.simplification_task_id = task_simplify.id
        dataset.simplification_progress = 'Started'
        dataset.save(
            update_fields=['simplification_task_id',
                           'simplification_progress']
        )
        views = DatasetView.objects.filter(
            dataset=dataset
        )
        for view in views:
            # check for view in dataset that inherits tiling config
            tiling_config_exists = DatasetViewTilingConfig.objects.filter(
                dataset_view=view
            ).exists()
            if tiling_config_exists:
                continue
            trigger_generate_vector_tile_for_view(view, export_data=False)

    def apply_to_datasetview(self, dataset_view_uuid, configs):
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view
        ).delete()
        for config in configs:
            tiling_config = DatasetViewTilingConfig.objects.create(
                dataset_view=dataset_view,
                zoom_level=config['zoom_level']
            )
            for level_config in config['admin_level_tiling_configs']:
                ViewAdminLevelTilingConfig.objects.create(
                    view_tiling_config=tiling_config,
                    level=level_config['level'],
                    simplify_tolerance=level_config['simplify_tolerance']
                )
        # reset dataset styles because zoom could be changed
        dataset = dataset_view.dataset
        dataset.styles = None
        dataset.style_source_name = ''
        dataset.save(update_fields=['styles', 'style_source_name'])
        # Trigger simplification
        if dataset_view.simplification_task_id:
            res = AsyncResult(dataset_view.simplification_task_id)
            if not res.ready():
                app.control.revoke(
                    dataset_view.simplification_task_id,
                    terminate=True
                )
        task_simplify = simplify_geometry_in_view.delay(dataset_view.id)
        dataset_view.simplification_task_id = task_simplify.id
        dataset_view.simplification_progress = 'Started'
        dataset_view.save(
            update_fields=['simplification_task_id',
                           'simplification_progress']
        )
        trigger_generate_vector_tile_for_view(dataset_view,
                                              export_data=False)

    def post(self, request, *args, **kwargs):
        object_uuid = request.data.get('object_uuid')
        # dataset or datasetview
        object_type = request.data.get('object_type')
        session = request.data.get('session')
        configs = self.get_tiling_configs_from_session(session)
        if object_type == 'dataset':
            self.apply_to_dataset(object_uuid, configs)
        elif object_type == 'datasetview':
            self.apply_to_datasetview(object_uuid, configs)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        # once finished, remove the temporary tiling configs
        TemporaryTilingConfig.objects.filter(
            session=session
        ).delete()
        return Response(status=204)


class TilingConfigCheckStatus(AzureAuthRequiredMixin, APIView):
    """
    Check simplification and vector tiles status.
    """
    permission_classes = [IsAuthenticated]

    def get_dataset_status(self, dataset):
        status = (
            'Done' if dataset.simplification_progress and
            'finished' in dataset.simplification_progress else
            'Processing'
        )
        progress = dataset.simplification_progress
        return status, progress

    def get(self, request, *args, **kwargs):
        object_type = kwargs.get('object_type')
        object_uuid = kwargs.get('uuid')
        object_id = None
        simplification_status = None
        simplification_progress = ''
        tiling_status = None
        tiling_progress = ''
        module = ''

        if object_type == 'dataset':
            dataset = get_object_or_404(
                Dataset,
                uuid=object_uuid
            )
            object_id = dataset.id
            simplification_status, simplification_progress = (
                self.get_dataset_status(dataset)
            )
            view_resources = DatasetViewResource.objects.filter(
                dataset_view__dataset=dataset
            )
            module = dataset.module.name
        elif object_type == 'datasetview':
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=object_uuid
            )
            module = dataset_view.dataset.module.name
            object_id = dataset_view.id
            if dataset_view.simplification_progress:
                simplification_status = (
                    'Done' if dataset_view.simplification_progress and
                    'finished' in dataset_view.simplification_progress else
                    'Processing'
                )
                simplification_progress = dataset_view.simplification_progress
            else:
                simplification_status, simplification_progress = (
                    self.get_dataset_status(dataset_view.dataset)
                )
            view_resources = DatasetViewResource.objects.filter(
                dataset_view=dataset_view
            )
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        view_resources = view_resources.aggregate(
            Avg('vector_tiles_progress')
        )
        tiling_progress = (
            view_resources['vector_tiles_progress__avg'] if
            view_resources['vector_tiles_progress__avg'] else 0
        )
        tiling_status = (
            'Done' if isclose(tiling_progress, 100, abs_tol=1e-4) else
            'Processing'
        )
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
                'vector_tiles': {
                    'status': tiling_status,
                    'progress': round(tiling_progress, 2)
                }
            }
        )


class UpdateDatasetTilingConfig(AzureAuthRequiredMixin,
                                DatasetManagePermission, APIView):
    """
    Update dataset tiling config
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        serializers = []
        zoom_levels = []
        for data in request.data:
            serializer = TilingConfigSerializer(
                data=data,
                many=False,
                context={
                    'zoom_levels': zoom_levels,
                    'current_zoom': data['zoom_level']
                }
            )
            serializer.is_valid(raise_exception=True)
            serializers.append(serializer)
            zoom_levels.append(serializer.validated_data['zoom_level'])
        for serializer in serializers:
            serializer.save(dataset=dataset)
        if not settings.DEBUG:
            # Trigger simplification
            if dataset.simplification_task_id:
                res = AsyncResult(dataset.simplification_task_id)
                if not res.ready():
                    app.control.revoke(
                        dataset.simplification_task_id,
                        terminate=True
                    )
            task_simplify = simplify_geometry_in_dataset.delay(dataset.id)
            dataset.simplification_task_id = task_simplify.id
            dataset.simplification_progress = 'Started'
            dataset.save(
                update_fields=['simplification_task_id',
                               'simplification_progress']
            )
        return Response(status=204)


class UpdateDatasetViewTilingConfig(AzureAuthRequiredMixin, APIView):
    """
    Update dataset view tiling config
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        dataset_view_uuid = kwargs.get('view')
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        serializers = []
        zoom_levels = []
        for data in request.data:
            serializer = ViewTilingConfigSerializer(
                data=data,
                many=False,
                context={
                    'zoom_levels': zoom_levels,
                    'current_zoom': data['zoom_level']
                }
            )
            serializer.is_valid(raise_exception=True)
            serializers.append(serializer)
            zoom_levels.append(serializer.validated_data['zoom_level'])
        for serializer in serializers:
            serializer.save(dataset_view=dataset_view)
        if not settings.DEBUG:
            # Trigger simplification
            if dataset_view.simplification_task_id:
                res = AsyncResult(dataset_view.simplification_task_id)
                if not res.ready():
                    app.control.revoke(
                        dataset_view.simplification_task_id,
                        terminate=True
                    )
            task_simplify = simplify_geometry_in_view.delay(dataset_view.id)
            dataset_view.simplification_task_id = task_simplify.id
            dataset_view.simplification_progress = 'Started'
            dataset_view.save(
                update_fields=['simplification_task_id',
                               'simplification_progress']
            )
            trigger_generate_vector_tile_for_view(dataset_view,
                                                  export_data=False)
        return Response(status=204)
