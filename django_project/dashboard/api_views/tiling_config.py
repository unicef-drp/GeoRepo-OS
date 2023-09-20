import uuid
from django.shortcuts import get_object_or_404
from django.db.models.expressions import RawSQL
from django.db.models import F, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from azure_auth.backends import AzureAuthRequiredMixin
from django.utils import timezone
from georepo.models import (
    Dataset,
    DatasetView,
    DatasetViewResource,
    GeographicalEntity
)
from georepo.models.dataset_tile_config import (
    DatasetTilingConfig, TemporaryTilingConfig,
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
from georepo.utils.dataset_view import (
    get_view_tiling_status
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


class PreviewTempTilingConfigAPIView(AzureAuthRequiredMixin, APIView):
    """
    Fetch temporary tiling config for preview
    """
    permission_classes = [IsAuthenticated]

    def get_max_min_zoom(self, session):
        zoom_levels = TemporaryTilingConfig.objects.filter(
            session=session
        ).order_by('zoom_level').values_list(
            'zoom_level',
            flat=True
        ).distinct()
        if zoom_levels:
            return zoom_levels[0], zoom_levels[len(zoom_levels) - 1]
        return 0, 0

    def prepare_response(self, session, entities, adm0_id = None):
        # retrieve list of adm0
        adm0 = entities.filter(
            level=0
        ).order_by('label').values('id', 'label')
        first_adm0 = adm0_id or adm0[0]['id']
        min_zoom, max_zoom = self.get_max_min_zoom(session)
        dataset_levels = entities.filter(
            Q(ancestor=first_adm0) |
            (Q(ancestor__isnull=True) & Q(id=first_adm0))
        ).order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        level_result = []
        # Generate from 0 - 6 admin levels
        entity_levels = [x for x in range(7)]
        for level in entity_levels:
            simplify_per_level = {
                'level': level,
                'factors': [],
                'has_data': level in dataset_levels
            }
            configs = TemporaryTilingConfig.objects.filter(
                session=session,
                level=level
            ).order_by('zoom_level')
            for config in configs:
                simplify_per_level['factors'].append({
                    'zoom_level': config.zoom_level,
                    'simplify': config.simplify_tolerance
                })
            level_result.append(simplify_per_level)
        return {
            'levels': level_result,
            'countries': adm0,
            'max_zoom': max_zoom,
            'min_zoom': min_zoom
        }

    def get_dataset_levels(self, session, dataset_uuid, adm0_id = None):
        dataset = get_object_or_404(Dataset, uuid=dataset_uuid)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True
        )
        return self.prepare_response(session, entities, adm0_id)

    def get_view_levels(self, session, view_uuid, adm0_id = None):
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
        return self.prepare_response(session, entities, adm0_id)

    def get(self, request, *args, **kwargs):
        session = kwargs.get('session')
        dataset_uuid = request.GET.get('dataset_uuid', None)
        view_uuid = request.GET.get('view_uuid', None)
        adm0_id = request.GET.get('adm0_id', None)
        if dataset_uuid:
            return Response(
                status=200,
                data=self.get_dataset_levels(session, dataset_uuid, adm0_id)
            )
        elif view_uuid:
            return Response(
                status=200,
                data=self.get_view_levels(session, view_uuid, adm0_id)
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


class ConfirmTemporaryTilingConfigAPIView(TemporaryTilingConfigAPIView):
    """
    Confirm and apply temporary tiling config
    """
    permission_classes = [IsAuthenticated]

    def apply_to_dataset(self, dataset_uuid, configs, overwrite_view=False):
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        DatasetTilingConfig.objects.filter(
            dataset=dataset
        ).delete()
        for idx, config in enumerate(configs):
            tiling_config = DatasetTilingConfig(
                dataset=dataset,
                zoom_level=config['zoom_level']
            )
            # only trigger
            if idx > 0:
                tiling_config.skip_signal = True
            tiling_config.save()
            for level_config in config['admin_level_tiling_configs']:
                AdminLevelTilingConfig.objects.create(
                    dataset_tiling_config=tiling_config,
                    level=level_config['level'],
                    simplify_tolerance=level_config['simplify_tolerance']
                )

        # reset dataset styles because zoom could be changed
        dataset.styles = None
        dataset.style_source_name = ''
        dataset.is_simplified = False
        dataset.save(update_fields=[
            'styles', 'style_source_name', 'is_simplified'
        ])

    def apply_to_datasetview(self, dataset_view_uuid, configs):
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=dataset_view_uuid
        )
        DatasetViewTilingConfig.objects.filter(
            dataset_view=dataset_view
        ).delete()
        for idx, config in enumerate(configs):
            tiling_config = DatasetViewTilingConfig(
                dataset_view=dataset_view,
                zoom_level=config['zoom_level']
            )
            if idx > 0:
                tiling_config.skip_signal = True
            tiling_config.save()
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
        dataset.save(
            update_fields=['styles', 'style_source_name', 'is_simplified']
        )

    def post(self, request, *args, **kwargs):
        object_uuid = request.data.get('object_uuid')
        # dataset or datasetview
        object_type = request.data.get('object_type')
        session = request.data.get('session')
        overwrite_view = request.data.get('overwrite_view', False)
        configs = self.get_tiling_configs_from_session(session)
        if object_type == 'dataset':
            self.apply_to_dataset(object_uuid, configs, overwrite_view)
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
        tiling_status, tiling_progress = (
            get_view_tiling_status(view_resources)
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
