import json
import math
import uuid
from datetime import datetime

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.db import connection
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.paginator import Paginator
from core.models.preferences import SitePreferences
from azure_auth.backends import AzureAuthRequiredMixin

from georepo.models import (
    GeographicalEntity,
    Dataset,
    DatasetView,
    Module
)
from dashboard.models import (
    EntitiesUserConfig,
    LayerUploadSession,
    PRE_PROCESSING
)
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    EntityUploadChildLv1,
    REVIEWING as UPLOAD_REVIEWING
)
from dashboard.tools.entity_query import (
    generate_entity_query,
    generate_entity_query_map,
    generate_entity_query_map_for_view,
    generate_entity_query_map_for_temp
)
from georepo.serializers.dataset import (
    DatasetAdminLevelNameSerializer,
    DatasetBoundaryTypeSerializer
)
from dashboard.serializers.dataset import (
    DatasetSerializer
)
from dashboard.serializers.entity import (
    DasboardDatasetEntityListSerializer
)
from georepo.utils.tile_configs import populate_tile_configs
from georepo.validation.layer_validation import retrieve_layer0_default_codes
from dashboard.tools.dataset_styles import (
    replace_source_tile_url,
    generate_default_style,
    replace_maptiler_api_key
)
from dashboard.tools.admin_level_names import (
    populate_default_dataset_admin_level_names
)
from georepo.utils.module_import import module_function
from georepo.utils.permission import (
    get_dataset_for_user,
    get_view_permission_privacy_level,
    get_dataset_to_add_datasetview,
    READ_DATASET_PERMISSION_LIST,
    WRITE_DATASET_PERMISSION_LIST,
    MANAGE_DATASET_PERMISSION_LIST,
    OWN_DATASET_PERMISSION_LIST
)
from dashboard.api_views.common import (
    DatasetReadPermission,
    DatasetManagePermission
)

DATASET_SHORT_CODE_MAX_LENGTH = 4


class DasboardDatasetEntityList(AzureAuthRequiredMixin,
                                DatasetReadPermission, APIView):
    """
    Get entity list based on filter
    Method: POST
    data: {
        ... //filterdata
    }
    """
    permission_classes = [IsAuthenticated]

    def get_filter_obj(self, session: str, filter) -> EntitiesUserConfig:
        config = get_object_or_404(
            EntitiesUserConfig,
            uuid=session
        )
        config.filters = filter
        config.updated_at = datetime.now()
        config.save()
        return config

    def get_sort_attribute(self, sort_by, sort_direction):
        sortable_columns = [
            'id',
            'country',
            'level',
            'type',
            'name',
            'default_code',
            'code',
            'cucode',
            'updated',
            'rev',
            'status',
        ]
        if sort_by not in sortable_columns:
            return None, None
        if sort_direction not in ['asc', 'desc']:
            return None, None
        field_mapping = {
            'id': 'gg.id',
            'country': 'parent_0.label',
            'level': 'gg.level',
            'type': 'gg.type',
            'name': 'gg.label',
            'default_code': 'gg.internal_code',
            'code': 'gg.unique_code',
            'cucode': 'gg.concept_code',
            'updated': 'gg.start_date',
            'rev': 'gg.revision_number',
            'status': 'gg.is_approved'
        }
        return field_mapping[sort_by], sort_direction

    def do_run_query(
            self,
            dataset: Dataset,
            config: EntitiesUserConfig,
            sort_by,
            sort_direction,
            privacy_level):
        sort, direction = self.get_sort_attribute(sort_by, sort_direction)
        raw_sql, query_values = generate_entity_query(
            dataset,
            config,
            sort,
            direction,
            privacy_level
        )
        rows = []
        with connection.cursor() as cursor:
            cursor.execute(raw_sql, query_values)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def post(self, request, *args, **kwargs):
        dataset_id = kwargs.get('id')
        dataset = get_object_or_404(
            Dataset,
            id=dataset_id
        )
        page = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '50'))
        sort_by = request.GET.get('sort_by', None)
        sort_direction = request.GET.get('sort_direction', None)
        session = kwargs.get('session')
        config = self.get_filter_obj(session, request.data)
        # check for view uuid, may come from external user
        view_uuid = request.GET.get('view_uuid', None)
        dataset_view = None
        if view_uuid:
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=view_uuid
            )
        privacy_level = self.get_dataset_privacy_level(dataset, dataset_view)
        data = self.do_run_query(dataset, config, sort_by, sort_direction,
                                 privacy_level)
        paginator = Paginator(data, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                DasboardDatasetEntityListSerializer(
                    paginated_entities, many=True).data
            )
        return Response(status=200, data={
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        })


class DashboardDatasetFilter(AzureAuthRequiredMixin,
                             DatasetReadPermission, APIView):
    """
    Get filter for dataset and user
    """
    permission_classes = [IsAuthenticated]

    def create_session(self, dataset, user) -> EntitiesUserConfig:
        # fetch from recent one if any
        last_config = EntitiesUserConfig.objects.filter(
            dataset=dataset,
            user=user
        ).filter(
            Q(concept_ucode__isnull=True) |
            Q(concept_ucode__exact='')
        ).filter(
            Q(query_string__isnull=True) |
            Q(query_string__exact='')
        ).order_by('updated_at').last()
        if last_config:
            return last_config
        config = EntitiesUserConfig.objects.create(
            dataset=dataset,
            user=user,
            filters=(
                last_config.filters if last_config else {}
            )
        )
        return config

    def get(self, *args, **kwargs):
        dataset_id = kwargs.get('id')
        session = self.request.GET.get('session', None)
        dataset = get_object_or_404(
            Dataset,
            id=dataset_id
        )
        config = None
        if session and session != '':
            configs = EntitiesUserConfig.objects.filter(
                uuid=session
            )
            if configs.exists():
                config = configs.first()
            else:
                config = self.create_session(
                    dataset,
                    self.request.user)
        else:
            config = self.create_session(
                    dataset,
                    self.request.user)
        if config is None:
            return Response(status=404, data={
                'detail': 'Not found!'
            })
        response = {
            'filters': config.filters,
            'session': config.uuid
        }
        return Response(status=200, data=response)


class DashboardDatasetFilterValue(AzureAuthRequiredMixin,
                                  DatasetReadPermission, APIView):
    """
    Get filter value for given dataset and criteria
    """
    permission_classes = [IsAuthenticated]

    def fetch_available_country(self, dataset, privacy_level):
        return GeographicalEntity.objects.filter(
            dataset=dataset,
            level=0,
            privacy_level__lte=privacy_level
        ).exclude(label__isnull=True).exclude(
            label__exact='').order_by().values_list(
                'label',
                flat=True).distinct()

    def fetch_available_level(self, dataset, privacy_level):
        return GeographicalEntity.objects.filter(
            dataset=dataset,
            privacy_level__lte=privacy_level
        ).order_by().values_list('level', flat=True).distinct()

    def fetch_available_level_name(self, dataset, privacy_level):
        return GeographicalEntity.objects.filter(
            dataset=dataset,
            privacy_level__lte=privacy_level
        ).exclude(label__isnull=True).exclude(
            label__exact='').order_by().values_list(
                'label',
                flat=True).distinct()

    def fetch_available_type(self, dataset, privacy_level):
        return GeographicalEntity.objects.filter(
            dataset=dataset,
            privacy_level__lte=privacy_level
        ).order_by('type__label').values_list(
            'type__label',
            flat=True
        ).distinct()

    def fetch_available_revision(self, dataset, privacy_level):
        return GeographicalEntity.objects.filter(
            dataset=dataset,
            privacy_level__lte=privacy_level
        ).exclude(
            revision_number__isnull=True
        ).order_by().values_list('revision_number', flat=True).distinct()

    def fetch_status(self):
        return (
            'Pending',
            'Approved'
        )

    def get(self, *args, **kwargs):
        data = []
        dataset_id = kwargs.get('id')
        dataset = get_object_or_404(
            Dataset,
            id=dataset_id
        )
        # check for view uuid, may come from external user
        view_uuid = self.request.GET.get('view_uuid', None)
        dataset_view = None
        if view_uuid:
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=view_uuid
            )
        privacy_level = self.get_dataset_privacy_level(dataset, dataset_view)
        criteria = kwargs.get('criteria')
        if criteria == 'country':
            data = self.fetch_available_country(dataset, privacy_level)
        elif criteria == 'level':
            data = self.fetch_available_level(dataset, privacy_level)
        elif criteria == 'level_name':
            data = self.fetch_available_level_name(dataset, privacy_level)
        elif criteria == 'type':
            data = self.fetch_available_type(dataset, privacy_level)
        elif criteria == 'revision':
            data = self.fetch_available_revision(dataset, privacy_level)
        elif criteria == 'status':
            data = self.fetch_status()
        return Response(status=200, data=data)


class DatasetEntityDetail(AzureAuthRequiredMixin,
                          DatasetReadPermission, APIView):
    """
    Get entity bbox and geojson
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        geo_id = kwargs.get('entity_id')
        entity = get_object_or_404(
            GeographicalEntity,
            id=geo_id
        )
        data = {
            'bbox': entity.geometry.extent,
            'geom': json.loads(
                        entity.geometry.geojson
                    )
        }
        return Response(status=200, data=data)


class DatasetMVTTiles(APIView):
    """
    Generate vector tiles mvt.
    """
    permission_classes = [IsAuthenticated]

    def generate_tile(self, sql, query_values):
        rows = []
        tile = []
        with connection.cursor() as cursor:
            raw_sql = (
                'SELECT ST_AsMVT(tile.*, \'level_\' || tile.level, '
                '4096, \'geom\', \'id\') '
                'FROM ('
                f'{sql}'
                ') AS tile '
                'GROUP BY tile.level'
            )
            cursor.execute(raw_sql, query_values)
            rows = cursor.fetchall()
            for row in rows:
                tile.append(bytes(row[0]))
        return tile

    def do_run_query(
                        self,
                        dataset: Dataset,
                        config: EntitiesUserConfig,
                        z: int,
                        x: int,
                        y: int,
                        privacy_level
                    ):
        sql, query_values = (
            generate_entity_query_map(dataset, config, z, x, y, privacy_level)
        )
        return self.generate_tile(sql, query_values)

    def get(self, *args, **kwargs):
        session = kwargs.get('session', None)
        dataset_uuid = kwargs.get('dataset', None)
        level = kwargs.get('level', None)
        revised_entity_uuid = kwargs.get('revised_entity', None)
        revision = kwargs.get('revision', None)
        boundary_type = kwargs.get('boundary_type', None)
        if dataset_uuid and level and revised_entity_uuid:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
            config = EntitiesUserConfig()
            config.filters = {
                'level': [level],
                'ancestor': [revised_entity_uuid]
            }
        elif dataset_uuid and revision and boundary_type:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
            config = EntitiesUserConfig()
            config.filters = {
                'type': [boundary_type],
                'revision': [revision]
            }
        elif session.startswith('dataset_'):
            dataset_uuid = session.replace('dataset_', '')
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
            config = EntitiesUserConfig()
        else:
            config = get_object_or_404(
                EntitiesUserConfig,
                uuid=session
            )
            dataset = config.dataset
        privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset
        )
        tile = self.do_run_query(
            dataset,
            config,
            kwargs.get('z'),
            kwargs.get('x'),
            kwargs.get('y'),
            privacy_level
        )
        if not len(tile):
            raise Http404()
        return HttpResponse(
            tile,
            content_type="application/x-protobuf")


class DatasetMVTTilesView(DatasetMVTTiles):
    """
    Generate tiles for view.
    """

    def get(self, *args, **kwargs):
        session = kwargs.get('session', None)
        view_uuid = kwargs.get('dataset_view', None)
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=view_uuid
        )
        config = get_object_or_404(
            EntitiesUserConfig,
            uuid=session
        )
        privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        sql, query_values = (
            generate_entity_query_map_for_view(
                dataset_view,
                config,
                kwargs.get('z'),
                kwargs.get('x'),
                kwargs.get('y'),
                privacy_level
            )
        )
        tile = self.generate_tile(sql, query_values)
        if not len(tile):
            raise Http404()
        return HttpResponse(
            tile,
            content_type="application/x-protobuf")


class DatasetMVTTilesPreviewTilingConfig(DatasetMVTTiles):
    """
    Generate tiles for preview tiling config updates.
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        session = kwargs.get('session')
        dataset_uuid = kwargs.get('dataset', None)
        dataset = None
        if dataset_uuid:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
        view_uuid = kwargs.get('dataset_view', None)
        dataset_view = None
        if view_uuid:
            dataset_view = DatasetView.objects.filter(
                uuid=view_uuid
            ).select_related('dataset').first()
            if dataset_view:
                dataset = dataset_view.dataset
        if dataset is None and dataset_view is None:
            raise Http404()
        sql, query_values = (
            generate_entity_query_map_for_temp(
                session,
                dataset,
                kwargs.get('z'),
                kwargs.get('x'),
                kwargs.get('y'),
                dataset_view=dataset_view
            )
        )
        tile = self.generate_tile(sql, query_values)
        if not len(tile):
            raise Http404()
        return HttpResponse(
            tile,
            content_type="application/x-protobuf")


class DeleteDataset(AzureAuthRequiredMixin, UserPassesTestMixin, APIView):
    """
    API view to delete a dataset
    """
    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        # test if dataset is empty
        entity_count = GeographicalEntity.objects.filter(
            dataset__id=self.kwargs.get('id'),
            is_approved=True
        ).count()
        if entity_count > 0:
            return False
        dataset = Dataset.objects.get(
            id=self.kwargs.get('id'))
        return self.request.user.has_perm('delete_dataset', dataset)

    def post(self, request, *args, **kwargs):
        dataset = Dataset.objects.get(id=kwargs.get('id'))
        dataset.delete()
        return Response(status=200)


class DatasetDetail(AzureAuthRequiredMixin, DatasetReadPermission, APIView):
    """
    Return dataset detail
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        id = kwargs.get('id')
        if id.isnumeric():
            dataset = Dataset.objects.get(
                id=id
            )
        else:
            dataset = Dataset.objects.get(
                uuid=id
            )
        serializer = DatasetSerializer(
            dataset,
            context={
                'user': request.user
            }
        )
        return Response(serializer.data)


class GroupDatasetList(AzureAuthRequiredMixin, APIView):
    """
    View to list all datasets
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        is_create_view = self.request.GET.get('create_view', False)
        datasets = Dataset.objects.all().order_by('created_at')
        if is_create_view:
            datasets = datasets.filter(
                is_active=True
            )
            datasets = get_dataset_to_add_datasetview(
                self.request.user,
                datasets
            )
        else:
            datasets = get_dataset_for_user(
                self.request.user,
                datasets
            )
        serializer = DatasetSerializer(
            datasets,
            many=True,
            context={
                'user': request.user
            }
        )
        return Response(
            data=serializer.data
        )


class DatasetEntityList(AzureAuthRequiredMixin, APIView):
    """
    View to list all entities in dataset in upload_session
    """
    upload_session = None

    def get_entity_uploads_readonly(self, level_0_data):
        results = []
        entity_uploads = self.upload_session.entityuploadstatus_set.all()
        for entity_upload in entity_uploads:
            level1_children = EntityUploadChildLv1.objects.filter(
                entity_upload=entity_upload
            )
            rematched_children = level1_children.filter(
                is_parent_rematched=True
            )
            entity = (
                entity_upload.original_geographical_entity if
                entity_upload.original_geographical_entity else
                entity_upload.revised_geographical_entity
            )
            if entity:
                updated_by = (
                    entity.approved_by.username if entity.approved_by else
                    entity.dataset.created_by.username
                    if entity.dataset.created_by else ''
                )
                results.append({
                    'id': str(entity.id),
                    'country': entity.label,
                    'layer0_id': entity.internal_code,
                    'country_entity_id': entity.id,
                    'layer0_file': None,
                    'revision': entity.revision_number,
                    'max_level': (
                        entity_upload.max_level if
                        entity_upload.max_level
                        else entity_upload.max_level_in_layer
                    ),
                    'last_update': (
                        entity.approved_date if entity.approved_date
                        else entity.dataset.last_update
                    ),
                    'updated_by': updated_by,
                    'upload_id': entity_upload.id,
                    'has_rematched': rematched_children.exists(),
                    'ucode': entity.unique_code,
                    'total_level1_children': level1_children.count(),
                    'total_rematched_count': rematched_children.count(),
                    'is_selected': (
                        True if entity_upload.revised_geographical_entity
                        else False
                    ),
                    'max_level_in_layer': entity_upload.max_level_in_layer,
                    'is_available': (
                        True if entity_upload.revised_geographical_entity
                        else False
                    ),
                    'admin_level_names': (
                        entity_upload.admin_level_names if
                        entity_upload.admin_level_names else {}
                    )
                })
            elif entity_upload.revised_entity_id:
                layer0_file = None
                if level_0_data:
                    layer0 = (
                        [(layer0, idx) for idx, layer0 in
                            enumerate(level_0_data)
                            if layer0['layer0_id'] ==
                            entity_upload.revised_entity_id]
                    )
                    if layer0:
                        layer0_file = layer0[0][0]['layer0_file']
                # new data level 0 but not selected by user
                results.append({
                    'id': str(uuid.uuid4()),
                    'country': entity_upload.revised_entity_name,
                    'layer0_id': entity_upload.revised_entity_id,
                    'country_entity_id': None,
                    'layer0_file': layer0_file,
                    'revision': None,
                    'max_level': (
                        entity_upload.max_level if
                        entity_upload.max_level
                        else entity_upload.max_level_in_layer
                    ),
                    'last_update': None,
                    'updated_by': None,
                    'upload_id': entity_upload.id,
                    'has_rematched': rematched_children.exists(),
                    'ucode': None,
                    'total_level1_children': level1_children.count(),
                    'total_rematched_count': rematched_children.count(),
                    'is_selected': False,
                    'max_level_in_layer': entity_upload.max_level_in_layer,
                    'is_available': False,
                    'admin_level_names': (
                        entity_upload.admin_level_names if
                        entity_upload.admin_level_names else {}
                    )
                })
        return results

    def get_entity_uploads(self, level_0_data, default_max_level):
        results = []
        entity_uploads = (
            self.upload_session.entityuploadstatus_set.all()
            .order_by('id')
        )
        has_selection = self.upload_session.entityuploadstatus_set.exclude(
            max_level=''
        ).exists()
        review_in_progress = EntityUploadStatus.objects.filter(
            upload_session__dataset=self.upload_session.dataset,
            status=UPLOAD_REVIEWING
        ).exclude(
            original_geographical_entity__isnull=True
        ).order_by('original_geographical_entity').values_list(
            'original_geographical_entity', flat=True
        ).distinct()
        for entity_upload in entity_uploads:
            entity = entity_upload.original_geographical_entity
            level1_children = EntityUploadChildLv1.objects.filter(
                entity_upload=entity_upload
            )
            rematched_children = level1_children.filter(
                is_parent_rematched=True
            )
            layer0_id = (
                entity.internal_code if entity
                else entity_upload.revised_entity_id
            )
            layer0_file = None
            if level_0_data:
                layer0 = (
                    [(layer0, idx) for idx, layer0 in
                        enumerate(level_0_data)
                        if layer0['layer0_id'] == layer0_id]
                )
                if layer0:
                    layer0_id = layer0[0][0]['layer0_id']
                    layer0_file = layer0[0][0]['layer0_file']

            is_selected = False
            if entity_upload.status != '':
                is_selected = (
                    True
                )
            else:
                # always set True if comes from layer pre-processing
                is_selected = not has_selection
            if entity:
                updated_by = (
                    entity.approved_by.username if entity.approved_by else
                    entity.dataset.created_by.username
                    if entity.dataset.created_by else ''
                )
                # check whether this entity is in REVIEW process
                # inside other session
                is_available = entity.id not in review_in_progress
                results.append({
                    'id': str(entity.id),
                    'country': entity.label,
                    'layer0_id': layer0_id,
                    'country_entity_id': entity.id,
                    'layer0_file': layer0_file,
                    'revision': entity.revision_number,
                    'max_level': (
                        entity_upload.max_level if
                        entity_upload.max_level
                        else entity_upload.max_level_in_layer
                    ),
                    'last_update': (
                        entity.approved_date if entity.approved_date
                        else entity.dataset.last_update
                    ),
                    'updated_by': updated_by,
                    'upload_id': entity_upload.id,
                    'has_rematched': rematched_children.exists(),
                    'ucode': entity.unique_code,
                    'total_level1_children': level1_children.count(),
                    'total_rematched_count': rematched_children.count(),
                    'is_selected': is_selected,
                    'max_level_in_layer': entity_upload.max_level_in_layer,
                    'is_available': is_available,
                    'admin_level_names': (
                        entity_upload.admin_level_names if
                        entity_upload.admin_level_names else {}
                    )
                })
            elif entity_upload.revised_entity_id:
                # level 0 uploads, new data
                results.append({
                    'id': str(uuid.uuid4()),
                    'country': entity_upload.revised_entity_name,
                    'layer0_id': layer0_id,
                    'country_entity_id': None,
                    'layer0_file': layer0_file,
                    'revision': None,
                    'max_level': (
                        entity_upload.max_level if
                        entity_upload.max_level
                        else entity_upload.max_level_in_layer
                    ),
                    'last_update': None,
                    'updated_by': None,
                    'upload_id': entity_upload.id,
                    'has_rematched': rematched_children.exists(),
                    'ucode': None,
                    'total_level1_children': level1_children.count(),
                    'total_rematched_count': rematched_children.count(),
                    'is_selected': is_selected,
                    'max_level_in_layer': entity_upload.max_level_in_layer,
                    'is_available': True,
                    'admin_level_names': (
                        entity_upload.admin_level_names if
                        entity_upload.admin_level_names else {}
                    )
                })
            else:
                # country not found from matching
                # this case is possible only when
                # threshold is being applied (if any)
                parent_entity_id = (
                    level1_children.first().parent_entity_id if
                    level1_children.exists() else 'Unknown'
                )
                results.append({
                    'id': str(uuid.uuid4()),
                    'country': 'No matching country',
                    'layer0_id': parent_entity_id,
                    'country_entity_id': None,
                    'layer0_file': None,
                    'revision': None,
                    'max_level': default_max_level,
                    'last_update': None,
                    'updated_by': None,
                    'upload_id': entity_upload.id,
                    'has_rematched': False,
                    'ucode': None,
                    'total_level1_children': level1_children.count(),
                    'total_rematched_count': 0,
                    'is_selected': False,
                    'is_available': True,
                    'admin_level_names': {}
                })
        return results

    def get(self, request, *args, **kwargs):
        dataset = None
        level_0_data = []
        is_level_0_upload = False
        available_levels = []
        default_max_level = -1

        session_id = request.GET.get('session', None)
        if session_id:
            self.upload_session = (
                LayerUploadSession.objects.get(id=session_id)
            )
            dataset = self.upload_session.dataset

            # retrieve max levels available in current upload session
            available_levels = (
                self.upload_session.layerfile_set.values_list(
                    'level', flat=True
                ).order_by('-level')
            )
            default_max_level = (
                available_levels[0] if available_levels else -1
            )
            # retrieve level 0 data
            level_0_data = retrieve_layer0_default_codes(
                self.upload_session,
                default_max_level
            )
            is_level_0_upload = len(level_0_data) > 0

        if not dataset:
            raise Http404()
        if not self.upload_session:
            raise Http404()

        results = []
        if self.upload_session.is_read_only():
            # fetch existing entity uploads
            results = self.get_entity_uploads_readonly(level_0_data)
        elif self.upload_session.status != PRE_PROCESSING:
            # upload start from admin_level 1, then check for parent matching
            results = self.get_entity_uploads(level_0_data, default_max_level)

        return Response(
            data={
                'is_level_0_upload': is_level_0_upload,
                'auto_matched_parent_ready': (
                    self.upload_session.auto_matched_parent_ready
                ),
                'status': self.upload_session.status,
                'results': results,
                'available_levels': available_levels,
                'is_read_only': self.upload_session.is_read_only(),
                'progress': self.upload_session.progress
            }
        )


class CreateDataset(AzureAuthRequiredMixin,
                    APIView):
    """
    API view to create a dataset
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        name = request.data.get('name')
        description = request.data.get('description')
        short_code = request.data.get('short_code', None)
        max_privacy_level = request.data.get('max_privacy_level', 4)
        min_privacy_level = request.data.get('min_privacy_level', 1)
        module_id = request.data.get('module_id')
        module = get_object_or_404(
            Module,
            id=module_id
        )
        if not request.user.has_perm('module_add_dataset', module):
            raise PermissionDenied(
                f'You are not allowed to create dataset in {module.name}'
            )
        is_short_code_valid, error = (
            CheckDatasetShortCode.check_dataset_short_code(short_code)
        )
        if not is_short_code_valid:
            return Response(status=400, data={
                'detail': error
            })

        dataset = Dataset.objects.create(
            label=name,
            description=description,
            module=module,
            created_by=request.user,
            geometry_similarity_threshold_new=(
                SitePreferences.preferences().
                geometry_similarity_threshold_new
            ),
            geometry_similarity_threshold_old=(
                SitePreferences.preferences().
                geometry_similarity_threshold_old
            ),
            short_code=short_code,
            max_privacy_level=max_privacy_level,
            min_privacy_level=min_privacy_level
        )
        populate_tile_configs(dataset.id)
        populate_default_dataset_admin_level_names(dataset)
        serializer = DatasetSerializer(
            dataset,
            context={
                'user': request.user
            }
        )
        return Response(status=201, data=serializer.data)


class DatasetStyle(AzureAuthRequiredMixin, APIView):
    """
    Get Dataset Style config
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_view_uuid = kwargs.get('dataset_view', None)
        if dataset_view_uuid:
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=dataset_view_uuid
            )
            dataset = dataset_view.dataset
        else:
            dataset_uuid = kwargs.get('dataset')
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
        session = None
        as_download = request.GET.get('download', False)
        # for download, give the dataset without any session filter
        if not as_download:
            session = request.GET.get('session', None)
        level = kwargs.get('level', None)
        revised_entity = kwargs.get('revised_entity', None)
        revision = kwargs.get('revision', None)
        boundary_type = kwargs.get('boundary_type', None)
        styles = {}
        if dataset.styles:
            # return the style with session
            styles = replace_source_tile_url(
                request,
                dataset.styles,
                dataset.style_source_name,
                dataset,
                session=session,
                revised_entity=revised_entity,
                level=level,
                revision=revision,
                boundary_type=boundary_type,
                dataset_view_uuid=dataset_view_uuid
            )
        else:
            # generate default style with session
            styles = generate_default_style(
                request,
                dataset,
                session=session,
                revised_entity=revised_entity,
                level=level,
                revision=revision,
                boundary_type=boundary_type,
                dataset_view_uuid=dataset_view_uuid
            )
        styles = replace_maptiler_api_key(styles)
        if as_download:
            response = HttpResponse(
                json.dumps(styles),
                status=200,
                content_type='application/json'
            )
            response['Content-Disposition'] = (
                'attachment; filename=styles.json'
            )
            return response

        return Response(
            status=200,
            data=styles,
            content_type="application/json"
        )


class UpdateDatasetStyle(AzureAuthRequiredMixin,
                         DatasetManagePermission, APIView):
    """
    Update Dataset Style config
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        source_name = kwargs.get('source_name')
        dataset.style_source_name = source_name
        dataset.styles = replace_source_tile_url(
            request,
            request.data,
            source_name,
            dataset
        )
        dataset.save()
        return Response(status=204)


class CheckDatasetShortCode(AzureAuthRequiredMixin, APIView):
    """
    Check if dataset short_code is available
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def check_dataset_short_code(short_code, dataset=None):
        """Return True if short_code is available"""
        if len(short_code) != DATASET_SHORT_CODE_MAX_LENGTH:
            return False, (
                'ShortCode must be '
                f'{DATASET_SHORT_CODE_MAX_LENGTH} characters'
            )
        check_dataset = Dataset.objects.filter(
            short_code=short_code
        )
        if dataset:
            check_dataset = check_dataset.exclude(
                id=dataset.id
            )
        is_available = not check_dataset.exists()
        error = None
        if not is_available:
            error = f'{short_code} has been used by other dataset'
        return is_available, error

    def post(self, request, *args, **kwargs):
        dataset_uuid = request.data.get('dataset', None)
        short_code = request.data.get('short_code')
        dataset = None
        if dataset_uuid:
            dataset = Dataset.objects.get(
                uuid=dataset_uuid
            )
        is_available, error = self.check_dataset_short_code(
            short_code,
            dataset
        )
        return Response(status=200, data={
            'is_available': is_available,
            'error': error
        })


class UpdateDataset(AzureAuthRequiredMixin, DatasetManagePermission, APIView):
    """
    Update Dataset name, threshold values
    """
    permission_classes = [IsAuthenticated]

    def check_own_permission(self, user, dataset):
        permissions = list(
            set(OWN_DATASET_PERMISSION_LIST) -
            set(MANAGE_DATASET_PERMISSION_LIST) -
            set(WRITE_DATASET_PERMISSION_LIST) -
            set(READ_DATASET_PERMISSION_LIST)
        )
        has_all_perms = True
        for permission in permissions:
            if not self.request.user.has_perm(permission, dataset):
                has_all_perms = False
                break
        return has_all_perms

    def post(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )

        name = request.data.get('name', None)
        old_name = dataset.label
        # check if dataset name is changed
        if name and name != old_name:
            dataset.label = name
        # update thresholds
        dataset.geometry_similarity_threshold_new = (
            request.data.get('geometry_similarity_threshold_new')
        )
        dataset.geometry_similarity_threshold_old = (
            request.data.get('geometry_similarity_threshold_old')
        )
        dataset.generate_adm0_default_views = (
            request.data.get('generate_adm0_default_views')
        )
        if dataset.generate_adm0_default_views:
            generate_adm0 = module_function(
                dataset.module.code_name,
                'config',
                'generate_adm0_default_views'
            )
            generate_adm0(dataset)
        tmp_active = dataset.is_active
        dataset.is_active = request.data.get('is_active')
        if not dataset.is_active and tmp_active:
            # deprecate dataset action
            # validate if user has own permission
            if not self.check_own_permission(request.user, dataset):
                return HttpResponseForbidden('No permission')
            dataset.deprecated_at = datetime.now()
            dataset.deprecated_by = request.user
        elif dataset.is_active and not tmp_active:
            # activate dataset action
            # validate if user has own permission
            if not self.check_own_permission(request.user, dataset):
                return HttpResponseForbidden('No permission')
            dataset.deprecated_at = None
            dataset.deprecated_by = None
        dataset.save()
        return Response(status=204)


class DatasetAdminLevelNames(AzureAuthRequiredMixin,
                             DatasetManagePermission, APIView):
    """
    Fetch dataset admin level names
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        admin_level_names = dataset.datasetadminlevelname_set.all()
        return Response(
            status=200,
            data=DatasetAdminLevelNameSerializer(
                admin_level_names,
                many=True
            ).data
        )

    def post(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        serializers = DatasetAdminLevelNameSerializer(
            data=request.data,
            many=True,
            context={
                'user': self.request.user
            }
        )
        serializers.is_valid(raise_exception=True)
        serializers.save(dataset=dataset)
        return Response(status=204)


class DatasetBoundaryTypes(AzureAuthRequiredMixin,
                           DatasetManagePermission, APIView):
    """
    Fetch boundary types for dataset in boundary lines module
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        boundary_types = dataset.boundarytype_set.all()
        return Response(
            status=200,
            data=DatasetBoundaryTypeSerializer(
                boundary_types,
                many=True
            ).data
        )

    def post(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=dataset_uuid
        )
        serializers = DatasetBoundaryTypeSerializer(
            data=request.data,
            many=True,
            context={
                'user': self.request.user
            }
        )
        serializers.is_valid(raise_exception=True)
        serializers.save(dataset=dataset)
        return Response(status=204)
