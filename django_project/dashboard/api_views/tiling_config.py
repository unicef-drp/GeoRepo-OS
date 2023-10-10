from django.shortcuts import get_object_or_404
from django.db.models.expressions import RawSQL
from django.db.models import F, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.models import (
    Dataset,
    DatasetView,
    DatasetViewResource,
    GeographicalEntity
)
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig,
    AdminLevelTilingConfig
)
from georepo.models.dataset_view_tile_config import (
    DatasetViewTilingConfig,
    ViewAdminLevelTilingConfig
)
from georepo.serializers.entity import SimpleGeographicalGeojsonSerializer
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from dashboard.serializers.tiling_config import (
    TilingConfigSerializer,
    ViewTilingConfigSerializer
)
from dashboard.api_views.common import (
    DatasetManagePermission
)
from georepo.tasks.dataset_view import (
    check_affected_views_from_tiling_config
)
from georepo.utils.celery_helper import cancel_task


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


class CountriesTilingConfigAPIView(AzureAuthRequiredMixin, APIView):
    """
    Fetch country list for preview
    """
    permission_classes = [IsAuthenticated]

    def prepare_response(self, entities, adm0_id = None):
        # retrieve list of adm0
        adm0 = entities.filter(
            level=0
        ).order_by('label').values('id', 'label')
        first_adm0 = adm0_id or (adm0[0]['id'] if adm0 else None)
        dataset_levels = entities.filter(
            Q(ancestor=first_adm0) |
            (Q(ancestor__isnull=True) & Q(id=first_adm0))
        ).order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        return {
            'countries': adm0,
            'levels': dataset_levels
        }

    def get_dataset_levels(self, dataset_uuid, adm0_id = None):
        dataset = get_object_or_404(Dataset, uuid=dataset_uuid)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True
        )
        return self.prepare_response(entities, adm0_id)

    def get_view_levels(self, view_uuid, adm0_id = None):
        dataset_view = get_object_or_404(DatasetView, uuid=view_uuid)
        dataset = dataset_view.dataset
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        return self.prepare_response(entities, adm0_id)

    def get(self, request, *args, **kwargs):
        dataset_uuid = request.GET.get('dataset_uuid', None)
        view_uuid = request.GET.get('view_uuid', None)
        adm0_id = request.GET.get('adm0_id', None)
        if dataset_uuid:
            return Response(
                status=200,
                data=self.get_dataset_levels(dataset_uuid, adm0_id)
            )
        elif view_uuid:
            return Response(
                status=200,
                data=self.get_view_levels(view_uuid, adm0_id)
            )
        return Response(status=200)


class FetchGeoJsonPreview(AzureAuthRequiredMixin, APIView):
    """
    Fetch geojson for country and admin level for preview
    """
    permission_classes = [IsAuthenticated]

    def prepare_response(self, entities, adm0_id, level):
        if level == 0:
            entities = entities.filter(id=adm0_id)
        else:
            entities = entities.filter(ancestor_id=adm0_id)
        entities = entities.annotate(
            rhr_geom=ForcePolygonCCW(F('geometry'))
        )
        values = ['id', 'rhr_geom']
        entities = entities.order_by('id').values(*values)
        return Response(
            status=200,
            data=SimpleGeographicalGeojsonSerializer(
                entities,
                many=True
            ).data
        )

    def get_dataset_entities(self, dataset_uuid, adm0_id, level):
        dataset = get_object_or_404(Dataset, uuid=dataset_uuid)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True,
            level=level
        )
        return self.prepare_response(entities, adm0_id, level)

    def get_view_entities(self, view_uuid, adm0_id, level):
        dataset_view = get_object_or_404(DatasetView, uuid=view_uuid)
        dataset = dataset_view.dataset
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True,
            level=level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        return self.prepare_response(entities, adm0_id, level)

    def get(self, request, *args, **kwargs):
        dataset_uuid = request.GET.get('dataset_uuid', None)
        view_uuid = request.GET.get('view_uuid', None)
        adm0_id = int(request.GET.get('adm0_id'))
        level = int(request.GET.get('level'))
        if view_uuid:
            return self.get_view_entities(view_uuid, adm0_id, level)
        return self.get_dataset_entities(dataset_uuid, adm0_id, level)


class ApplyTilingConfigAPIView(AzureAuthRequiredMixin, APIView):
    """
    Apply tiling config to dataset/view.
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
        for data in configs:
            zoom_level = data['zoom_level']
            tiling_config = DatasetTilingConfig(
                dataset=dataset,
                zoom_level=zoom_level
            )
            # only trigger
            if zoom_level > 0:
                tiling_config.skip_signal = True
            tiling_config.save()
            for config in data['admin_level_tiling_configs']:
                AdminLevelTilingConfig.objects.create(
                    dataset_tiling_config=tiling_config,
                    level=config['level'],
                    simplify_tolerance=config['simplify_tolerance']
                )
        # reset dataset styles because zoom could be changed
        dataset.styles = None
        dataset.style_source_name = ''
        dataset.is_simplified = False
        dataset.sync_status = dataset.SyncStatus.OUT_OF_SYNC
        dataset.simplification_sync_status = dataset.SyncStatus.OUT_OF_SYNC
        dataset.save(update_fields=[
            'styles', 'style_source_name', 'is_simplified', 'sync_status',
            'simplification_sync_status'
        ])
        # trigger check affected views from dataset tiling config
        check_affected_views_from_tiling_config.delay(dataset.id)

    def apply_to_datasetview(self, dataset_view_uuid, configs):
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view
        ).delete()
        for data in configs:
            zoom_level = data['zoom_level']
            tiling_config = DatasetViewTilingConfig(
                dataset_view=dataset_view,
                zoom_level=zoom_level
            )
            # only trigger
            if zoom_level > 0:
                tiling_config.skip_signal = True
            tiling_config.save()
            for config in data['admin_level_tiling_configs']:
                ViewAdminLevelTilingConfig.objects.create(
                    view_tiling_config=tiling_config,
                    level=config['level'],
                    simplify_tolerance=config['simplify_tolerance']
                )
        # cancel ongoing task
        if dataset_view.simplification_task_id:
            cancel_task(dataset_view.simplification_task_id)
        if dataset_view.task_id:
            cancel_task(dataset_view.task_id)
        view_resources = DatasetViewResource.objects.filter(
            dataset_view=dataset_view
        )
        for view_resource in view_resources:
            if view_resource.vector_tiles_task_id:
                cancel_task(view_resource.vector_tiles_task_id)
        dataset_view.set_out_of_sync(
            tiling_config=True,
            vector_tile=True,
            product=False
        )

    def post(self, request, *args, **kwargs):
        object_uuid = kwargs.get('uuid')
        # dataset or datasetview
        object_type = kwargs.get('object_type')
        configs = request.data
        if object_type == 'dataset':
            self.apply_to_dataset(object_uuid, configs)
        elif object_type == 'datasetview':
            self.apply_to_datasetview(object_uuid, configs)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return Response(status=204)
