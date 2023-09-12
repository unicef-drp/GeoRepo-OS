import math
from django.db.models.expressions import RawSQL
from django.db.models import FilteredRelation, Q, Prefetch
from django.http import (
    Http404
)
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user

from georepo.utils.permission import (
    DatasetDetailAccessPermission,
    DatasetViewDetailAccessPermission,
    get_dataset_views_for_user,
    get_view_permission_privacy_level,
    check_user_has_view_permission
)
from georepo.api_views.api_cache import ApiCache
from georepo.models.dataset_view import (
    DatasetView,
    DATASET_VIEW_DATASET_TAG,
    DatasetViewResource
)
from georepo.models.entity import (
    EntityId,
    MAIN_ENTITY_ID_LIST,
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID
)
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.serializers.dataset_view import (
    DatasetViewItemSerializer,
    DatasetViewDetailSerializer,
    DatasetViewItemForUserSerializer
)
from georepo.serializers.common import APIErrorSerializer
from georepo.utils.unique_code import parse_unique_code
from georepo.utils.uuid_helper import get_uuid_value
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_VIEW_TAG,
    DOWNLOAD_DATA_TAG
)
from georepo.utils.api_parameters import common_api_params
from georepo.utils.permission import (
    EXTERNAL_READ_VIEW_PERMISSION_LIST
)
from georepo.utils.exporter_base import APIDownloaderBase
from georepo.utils.dataset_view import (
    get_view_resource_from_view
)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-view-list-by-dataset',
                tags=[SEARCH_VIEW_TAG],
                manual_parameters=[
                    openapi.Parameter(
                        'uuid', openapi.IN_PATH,
                        description='Dataset UUID',
                        type=openapi.TYPE_STRING
                    ),
                    *common_api_params
                ],
                responses={
                    200: openapi.Schema(
                        title='Dataset View List',
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'page': openapi.Schema(
                                title='Page Number',
                                type=openapi.TYPE_INTEGER
                            ),
                            'total_page': openapi.Schema(
                                title='Total Page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'page_size': openapi.Schema(
                                title='Total item in 1 page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'results': openapi.Schema(
                                title='Dataset view list',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties=(
                                        DatasetViewItemSerializer.Meta.
                                        swagger_schema_fields['properties']
                                    )
                                ),
                            )
                        },
                        example={
                            'page': 1,
                            'total_page': 10,
                            'page_size': 10,
                            'results': [
                                (
                                    DatasetViewItemSerializer.Meta.
                                    swagger_schema_fields['example']
                                )
                            ]
                        }
                    )
                }
            )
)
class DatasetViewList(ApiCache):
    """
    Get views by dataset.

    Return views:
    - name
    - uuid
    - description
    - dataset
    - last_update date time
    - vector tiles URL
    - bbox
    - tag list
    """
    permission_classes = [DatasetDetailAccessPermission]
    cache_model = DatasetView

    def get_response_data(self, request, *args, **kwargs):
        dataset_uuid = self.kwargs.get('uuid', None)
        page = int(request.GET.get('page', '1'))
        page_size = get_page_size(request)
        dataset = get_object_or_404(
            Dataset, uuid=dataset_uuid, module__is_active=True
        )
        self.check_object_permissions(request, dataset)
        # sort by id to make view with dataset tag on top
        dataset_views_1 = DatasetView.objects.filter(
            dataset__uuid=dataset_uuid,
            tags__name__in=[DATASET_VIEW_DATASET_TAG]
        ).select_related('dataset').prefetch_related(
            'tags',
            Prefetch(
                'datasetviewresource_set',
                queryset=DatasetViewResource.objects.filter(
                    entity_count__gt=0
                ),
            )
        ).order_by('id').distinct()
        dataset_views_1, user_privacy_level = get_dataset_views_for_user(
            self.request.user,
            dataset,
            dataset_views_1
        )
        dataset_views_2 = DatasetView.objects.filter(
            dataset__uuid=dataset_uuid
        ).select_related('dataset').prefetch_related(
            'tags',
            Prefetch(
                'datasetviewresource_set',
                queryset=DatasetViewResource.objects.filter(
                    entity_count__gt=0
                ),
            )
        ).exclude(
            tags__name__in=[DATASET_VIEW_DATASET_TAG]
        ).order_by('id').distinct()
        dataset_views_2, user_privacy_level = get_dataset_views_for_user(
            self.request.user,
            dataset,
            dataset_views_2
        )
        dataset_views = dataset_views_1.union(dataset_views_2)
        dataset_views = dataset_views.order_by('id')
        # get dict of unique_code and unique_code_version
        root_entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            level=0,
            is_approved=True,
            is_latest=True
        ).order_by('revision_number').values(
            'unique_code', 'unique_code_version'
        )
        # set pagination
        paginator = Paginator(dataset_views, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                DatasetViewItemSerializer(
                    paginated_entities,
                    many=True,
                    context={
                        'request': self.request,
                        'user_privacy_level': user_privacy_level,
                        'root_entities': root_entities
                    }
                ).data
            )
        return {
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        }, None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-view-list',
                tags=[SEARCH_VIEW_TAG],
                manual_parameters=[
                    *common_api_params
                ],
                responses={
                    200: openapi.Schema(
                        title='Dataset View List',
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'page': openapi.Schema(
                                title='Page Number',
                                type=openapi.TYPE_INTEGER
                            ),
                            'total_page': openapi.Schema(
                                title='Total Page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'page_size': openapi.Schema(
                                title='Total item in 1 page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'results': openapi.Schema(
                                title='Dataset view list',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties=(
                                        DatasetViewItemSerializer.Meta.
                                        swagger_schema_fields['properties']
                                    )
                                ),
                            )
                        },
                        example={
                            'page': 1,
                            'total_page': 10,
                            'page_size': 10,
                            'results': [
                                (
                                    DatasetViewItemSerializer.Meta.
                                    swagger_schema_fields['example']
                                )
                            ]
                        }
                    )
                }
            )
)
class DatasetViewListForUser(ApiCache):
    """
    Get views that user can access.

    Return views:
    - name
    - uuid
    - description
    - dataset name
    - last_update date time
    - vector tiles URL
    - bbox
    - tag list
    """

    permission_classes = [IsAuthenticated]
    cache_model = DatasetView

    def get_response_data(self, request, *args, **kwargs):
        page = int(request.GET.get('page', '1'))
        page_size = get_page_size(request)
        checker = ObjectPermissionChecker(request.user)
        views = (
            DatasetView.objects.select_related('dataset').filter(
                dataset__module__is_active=True
            ).prefetch_related(
                'tags',
                Prefetch(
                    'datasetviewresource_set',
                    queryset=DatasetViewResource.objects.filter(
                        entity_count__gt=0
                    ),
                )
            ).order_by(
                'name'
            )
        )
        permission_list = ['view_datasetview']
        permission_list.extend(EXTERNAL_READ_VIEW_PERMISSION_LIST)
        dataset_views = get_objects_for_user(
            request.user,
            permission_list,
            klass=views,
            use_groups=True,
            any_perm=True,
            accept_global_perms=False
        )
        # set pagination
        paginator = Paginator(dataset_views, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                DatasetViewItemForUserSerializer(
                    paginated_entities,
                    many=True,
                    context={
                        'request': self.request,
                        'obj_checker': checker
                    }
                ).data
            )
        return {
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        }, None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-view-detail',
                tags=[SEARCH_VIEW_TAG],
                manual_parameters=[],
                responses={
                    200: DatasetViewDetailSerializer
                }
            )
)
class DatasetViewDetail(ApiCache):
    """
    Find view detail

    Return detail of a view:
    - name
    - description
    - dataset
    - uuid
    - created / last update date time
    - status
    - vector tiles URL
    - tag list
    - admin levels
    - Other external code types in dataset view
    - bbox

    Requires View UUID, can be retrieved from API search-view-list
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    cache_model = DatasetView

    def get_response_data(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=uuid,
            dataset__module__is_active=True
        )
        self.check_object_permissions(request, dataset_view)
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        response_data = (
            DatasetViewDetailSerializer(
                dataset_view,
                context={
                    'user': request.user,
                    'request': request,
                    'user_privacy_level': user_privacy_level
                }
            ).data
        )
        return response_data, None


class DatasetViewExportDownload(APIDownloaderBase):
    """
    Download dataset view as given {format} in zip file

    Download zip file of requested format from dataset view
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="View UUID", type=openapi.TYPE_STRING
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[geojson, shapefile, kml, topojson]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset_view: DatasetView):
        output_format = self.get_output_format()
        results = []
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        # get resource for the privacy level
        resource = get_view_resource_from_view(
            dataset_view,
            user_privacy_level
        )
        if resource is None:
            return [], 0
        entities = GeographicalEntity.objects.filter(
            dataset=dataset_view.dataset,
            is_approved=True,
            privacy_level__lte=user_privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        levels = entities.order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        total_count = 0
        for level in levels:
            exported_name = f'adm{level}'
            file_path = self.get_resource_path(
                output_format['directory'],
                resource,
                exported_name,
                output_format['suffix']
            )
            if not self.check_exists(file_path):
                return [], 0
            results.append(file_path)
            # add metadata (for geojson)
            metadata_file_path = self.get_resource_path(
                output_format['directory'],
                resource,
                exported_name,
                '.xml'
            )
            if self.check_exists(metadata_file_path):
                results.append(metadata_file_path)
            total_count += 1
        self.append_readme(resource, output_format, results)
        return results, total_count

    @swagger_auto_schema(
        operation_id='download-dataset-view',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[uuid_param, format_param],
        responses={
            200: openapi.Schema(
                description=(
                    'Dataset zip file'
                ),
                type=openapi.TYPE_FILE
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=uuid,
            dataset__module__is_active=True
        )
        self.check_object_permissions(request, dataset_view)
        result_list, total_count = self.get_exported_files(dataset_view)
        if total_count == 0:
            raise Http404('The requested file does not exist')
        prefix_name, zip_file_name = self.get_output_names(dataset_view)
        return self.prepare_response(prefix_name, zip_file_name, result_list)


class DatasetViewExportDownloadByLevel(DatasetViewExportDownload):
    """
    Download dataset view as given {format} in zip file for {admin_level}

    Download zip file of requested format from dataset view
    """

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="View UUID",
        type=openapi.TYPE_STRING
    )
    level_param = openapi.Parameter(
        'admin_level', openapi.IN_PATH,
        description=(
            'Admin level'
        ),
        type=openapi.TYPE_INTEGER
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[geojson, shapefile, kml, topojson]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset_view: DatasetView):
        output_format = self.get_output_format()
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        # get resource for the privacy level
        resource = get_view_resource_from_view(
            dataset_view,
            user_privacy_level
        )
        if resource is None:
            return [], 0
        # admin level
        admin_level = self.kwargs.get('admin_level')
        results = []
        exported_name = f'adm{admin_level}'
        file_path = self.get_resource_path(
            output_format['directory'],
            resource,
            exported_name,
            output_format['suffix']
        )
        if not self.check_exists(file_path):
            return [], 0
        results.append(file_path)
        # add metadata (for geojson)
        metadata_file_path = self.get_resource_path(
            output_format['directory'],
            resource,
            exported_name,
            '.xml'
        )
        if self.check_exists(metadata_file_path):
            results.append(metadata_file_path)
        total_count = 1
        self.append_readme(resource, output_format, results)
        return results, total_count

    @swagger_auto_schema(
        operation_id='download-dataset-view-by-level',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[uuid_param, level_param, format_param],
        responses={
            200: openapi.Schema(
                description=(
                    'Dataset zip file'
                ),
                type=openapi.TYPE_FILE
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(DatasetViewExportDownloadByLevel, self).get(
            request, *args, **kwargs
        )


class DatasetViewExportDownloadByCountry(DatasetViewExportDownload):
    """
    Download dataset view as given {format} in zip file for Country

    Download zip file of requested format from dataset view for Country
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="View UUID", type=openapi.TYPE_STRING
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'Country ID Type; The list is available from '
            '/api/v1/id-type/. '
            'Example: PCode'
        ),
        type=openapi.TYPE_STRING
    )
    id_param = openapi.Parameter(
        'id', openapi.IN_PATH,
        description=(
            'ID value of the Country. '
            'Example: PAK'
        ),
        type=openapi.TYPE_STRING
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[geojson, shapefile, kml, topojson]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_adm0(self, dataset_view: DatasetView, privacy_level: int):
        """Retrieve adm0 with id_type and id value, may return multiple"""
        id_type = self.kwargs.get('id_type', None)
        id_type = id_type.lower() if id_type else None
        id_value = self.kwargs.get('id', None)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset_view.dataset,
            is_approved=True,
            level=0,
            privacy_level__lte=privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        if id_type in MAIN_ENTITY_ID_LIST:
            if id_type == UUID_ENTITY_ID:
                uuid_val = get_uuid_value(id_value)
                entities = entities.filter(
                    uuid_revision=uuid_val
                )
            elif id_type == CONCEPT_UUID_ENTITY_ID:
                uuid_val = get_uuid_value(id_value)
                entities = entities.filter(
                    uuid=uuid_val
                )
            elif id_type == CODE_ENTITY_ID:
                entities = entities.filter(
                    internal_code=id_value
                )
            elif id_type == UCODE_ENTITY_ID:
                try:
                    ucode, version = parse_unique_code(id_value)
                except ValueError:
                    return None
                entity_concept = GeographicalEntity.objects.filter(
                    unique_code=ucode,
                    unique_code_version=version,
                    dataset=dataset_view.dataset,
                    is_approved=True,
                    level=0,
                    privacy_level__lte=privacy_level
                )
                entity_concept = entity_concept.filter(
                    id__in=RawSQL(raw_sql, [])
                ).first()
                if entity_concept is None:
                    return None
                entities = entities.filter(
                    uuid=entity_concept.uuid
                )
            elif id_type == CONCEPT_UCODE_ENTITY_ID:
                entities = entities.filter(
                    concept_ucode=id_value
                )
        else:
            id_obj = EntityId.objects.filter(
                code__name__iexact=id_type
            ).first()
            if not id_obj:
                return None
            field_key = f'id_{id_obj.code.id}'
            annotations = {
                field_key: FilteredRelation(
                    'entity_ids',
                    condition=Q(entity_ids__code__id=id_obj.code.id)
                )
            }
            field_key = f'id_{id_obj.code.id}__value'
            entities = entities.annotate(**annotations)
            filter_by_idtype = {
                field_key: id_value
            }
            entities = entities.filter(**filter_by_idtype)
        entities = entities.order_by('-revision_number')
        return entities

    def get_exported_files(self, dataset_view: DatasetView):
        output_format = self.get_output_format()
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        # get resource for the privacy level
        resource = get_view_resource_from_view(
            dataset_view,
            user_privacy_level
        )
        if resource is None:
            return [], 0
        results = []
        adm0_list = self.get_adm0(dataset_view, user_privacy_level)
        adm0_count = adm0_list.count() if adm0_list is not None else 0
        if adm0_count == 0:
            return results, 0
        added_ucodes = []
        total_count = 0
        for adm0 in adm0_list:
            if adm0.unique_code in added_ucodes:
                # skip if it's the same entity
                continue
            entities = GeographicalEntity.objects.filter(
                dataset=dataset_view.dataset,
                is_approved=True,
                privacy_level__lte=user_privacy_level
            ).filter(
                Q(ancestor=adm0) |
                (Q(ancestor__isnull=True) & Q(id=adm0.id))
            )
            # raw_sql to view to select id
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(dataset_view.uuid))
            entities = entities.filter(
                id__in=RawSQL(raw_sql, [])
            )
            levels = entities.order_by('level').values_list(
                'level',
                flat=True
            ).distinct()
            for level in levels:
                exported_name = f'adm{level}'
                file_path = self.get_resource_path(
                    output_format['directory'],
                    resource,
                    exported_name,
                    output_format['suffix']
                )
                if not self.check_exists(file_path):
                    return [], 0
                results.append(file_path)
                # add metadata (for geojson)
                metadata_file_path = self.get_resource_path(
                    output_format['directory'],
                    resource,
                    exported_name,
                    '.xml'
                )
                if self.check_exists(metadata_file_path):
                    results.append(metadata_file_path)
            added_ucodes.append(adm0.unique_code)
            total_count += 1
        self.append_readme(resource, output_format, results)
        return results, total_count

    def get_adm0_view(self, dataset: Dataset, dataset_view: DatasetView,
                      view_type):
        """Retrieve adm0 with id_type and id value, may return multiple"""
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset,
            dataset_view=dataset_view
        )
        id_type = self.kwargs.get('id_type', None)
        id_type = id_type.lower() if id_type else None
        id_value = self.kwargs.get('id', None)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            level=0,
            privacy_level__lte=user_privacy_level
        )
        if id_type in MAIN_ENTITY_ID_LIST:
            if id_type == UUID_ENTITY_ID:
                uuid_val = get_uuid_value(id_value)
                entities = entities.filter(
                    uuid_revision=uuid_val
                )
            elif id_type == CONCEPT_UUID_ENTITY_ID:
                uuid_val = get_uuid_value(id_value)
                entities = entities.filter(
                    uuid=uuid_val
                )
            elif id_type == CODE_ENTITY_ID:
                entities = entities.filter(
                    internal_code=id_value
                )
            elif id_type == UCODE_ENTITY_ID:
                try:
                    ucode, version = parse_unique_code(id_value)
                except ValueError:
                    return None
                entity_concept = GeographicalEntity.objects.filter(
                    unique_code=ucode,
                    unique_code_version=version,
                    dataset=dataset,
                    is_approved=True,
                    level=0,
                    privacy_level__lte=user_privacy_level
                ).first()
                if entity_concept is None:
                    return None
                entities = entities.filter(
                    uuid=entity_concept.uuid
                )
            elif id_type == CONCEPT_UCODE_ENTITY_ID:
                entities = entities.filter(
                    concept_ucode=id_value
                )
        else:
            id_obj = EntityId.objects.filter(
                code__name__iexact=id_type
            ).first()
            if not id_obj:
                return None
            field_key = f'id_{id_obj.code.id}'
            annotations = {
                field_key: FilteredRelation(
                    'entity_ids',
                    condition=Q(entity_ids__code__id=id_obj.code.id)
                )
            }
            field_key = f'id_{id_obj.code.id}__value'
            entities = entities.annotate(**annotations)
            filter_by_idtype = {
                field_key: id_value
            }
            entities = entities.filter(**filter_by_idtype)
        entities = entities.order_by('-revision_number')
        entity = entities.first()
        if entity is None:
            return None
        other_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=view_type,
            default_ancestor_code=entity.unique_code
        ).first()
        if other_view:
            # check permission+min privacy level
            other_view_perm = (
                check_user_has_view_permission(
                    self.request.user,
                    other_view,
                    user_privacy_level) and
                user_privacy_level >= other_view.min_privacy_level
            )
            if not other_view_perm:
                other_view = None
        return other_view

    @swagger_auto_schema(
        operation_id='download-dataset-view-by-country',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[
            uuid_param,
            id_type_param,
            id_param,
            format_param
        ],
        responses={
            200: openapi.Schema(
                description=(
                    'Dataset zip file'
                ),
                type=openapi.TYPE_FILE
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=uuid,
            dataset__module__is_active=True
        )
        self.check_object_permissions(request, dataset_view)
        if (
            dataset_view.default_type and
            dataset_view.default_ancestor_code is None
        ):
            # change the view to correct view based on id+id_type
            other_view = self.get_adm0_view(
                dataset_view.dataset,
                dataset_view,
                dataset_view.default_type
            )
            if other_view is None:
                # return not found
                raise Http404('The requested file does not exist')
            kwargs['uuid'] = str(other_view.uuid)
        return super(DatasetViewExportDownloadByCountry, self).get(
            request, *args, **kwargs
        )


class DatasetViewExportDownloadByCountryAndLevel(
        DatasetViewExportDownloadByCountry):
    """
    Download dataset view as given {format} in zip file for Country and Level

    Download zip file of requested format from dataset view
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="View UUID", type=openapi.TYPE_STRING
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'Country ID Type; The list is available from '
            '/api/v1/id-type/. '
            'Example: PCode'
        ),
        type=openapi.TYPE_STRING
    )
    id_param = openapi.Parameter(
        'id', openapi.IN_PATH,
        description=(
            'ID value of the Country. '
            'Example: PAK'
        ),
        type=openapi.TYPE_STRING
    )
    level_param = openapi.Parameter(
        'admin_level', openapi.IN_PATH,
        description=(
            'Admin level'
        ),
        type=openapi.TYPE_INTEGER
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[geojson, shapefile, kml, topojson]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset_view: DatasetView):
        output_format = self.get_output_format()
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        # get resource for the privacy level
        resource = get_view_resource_from_view(
            dataset_view,
            user_privacy_level
        )
        if resource is None:
            return [], 0
        # admin level
        admin_level = self.kwargs.get('admin_level', None)
        results = []
        adm0_list = self.get_adm0(dataset_view, user_privacy_level)
        if not adm0_list:
            return results, 0
        added_ucodes = []
        total_count = 0
        for adm0 in adm0_list:
            if adm0.unique_code in added_ucodes:
                # skip if it's the same entity
                continue
            exported_name = f'adm{admin_level}'
            file_path = self.get_resource_path(
                output_format['directory'],
                resource,
                exported_name,
                output_format['suffix']
            )
            if not self.check_exists(file_path):
                return [], 0
            results.append(file_path)
            # add metadata (for geojson)
            metadata_file_path = self.get_resource_path(
                output_format['directory'],
                resource,
                exported_name,
                '.xml'
            )
            if self.check_exists(metadata_file_path):
                results.append(metadata_file_path)
            added_ucodes.append(adm0.unique_code)
            total_count += 1
        self.append_readme(resource, output_format, results)
        return results, total_count

    @swagger_auto_schema(
        operation_id='download-dataset-view-by-country-and-level',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[
            uuid_param,
            id_type_param,
            id_param,
            level_param,
            format_param
        ],
        responses={
            200: openapi.Schema(
                description=(
                    'Dataset zip file'
                ),
                type=openapi.TYPE_FILE
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(DatasetViewExportDownloadByCountryAndLevel, self).get(
            request, *args, **kwargs
        )
