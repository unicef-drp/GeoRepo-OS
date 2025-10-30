import math
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import (
    Http404
)
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from django.core.paginator import Paginator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework.response import Response

from core.mixins import APILoggingMixin
from georepo.models.base_task_request import PENDING
from georepo.models.dataset_tile_config import DatasetTilingConfig
from georepo.utils.permission import (
    ModuleAccessPermission,
    DatasetDetailAccessPermission,
    get_dataset_for_user,
    get_view_permission_privacy_level
)
from georepo.api_views.api_cache import ApiCache
from georepo.models import (
    GeographicalEntity,
    Dataset,
    Module
)
from georepo.models.export_request import (
    DatasetExportRequest,
    AVAILABLE_EXPORT_FORMAT_TYPES,
    ExportRequestStatusText
)
from georepo.serializers.common import APIErrorSerializer
from georepo.serializers.dataset import (
    DatasetItemSerializer,
    DetailedDatasetSerializer,
    DatasetExportRequestStatusSerializer
)
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_DATASET_TAG,
    SEARCH_ENTITY_TAG,
    DOWNLOAD_DATA_TAG
)
from georepo.utils.api_parameters import (
    common_api_params,
    search_param,
    sort_param,
    APISortBase
)
from georepo.utils.entity_query import validate_datetime
from georepo.tasks.dataset import dataset_exporter


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-dataset-list',
                tags=[SEARCH_DATASET_TAG],
                manual_parameters=[
                    openapi.Parameter(
                        'uuid', openapi.IN_PATH,
                        description="Module UUID", type=openapi.TYPE_STRING
                    ),
                    search_param, sort_param, *common_api_params
                ],
                responses={
                    200: openapi.Schema(
                        title='Dataset List',
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
                            'count': openapi.Schema(
                                title='Total Count',
                                type=openapi.TYPE_INTEGER
                            ),
                            'results': openapi.Schema(
                                title='List of dataset',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties=(
                                        DatasetItemSerializer.Meta.
                                        swagger_schema_fields['properties']
                                    )
                                ),
                            )
                        },
                        example={
                            'page': 1,
                            'total_page': 10,
                            'page_size': 10,
                            'count': 1,
                            'results': [
                                (
                                    DatasetItemSerializer.Meta.
                                    swagger_schema_fields['example']
                                )
                            ]
                        }
                    )
                }
            )
)
class DatasetList(ApiCache, APISortBase):
    """
    Get datasets by module

    Return datasets:
    - name
    - uuid
    - short_code
    - type (Module)
    - last_update date time
    """
    permission_classes = [ModuleAccessPermission]
    cache_model = Dataset
    use_cache = True
    sort_attribute_mapping = {
        'name': 'label',
        'is_favorite': 'is_preferred',
        'last_update': 'last_update',
        'short_code': 'short_code'
    }
    default_sort = ['-is_preferred', 'label']

    def get_response_data(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid')
        page = int(request.GET.get('page', '1'))
        page_size = get_page_size(request)
        module = get_object_or_404(
            Module, uuid=uuid, is_active=True
        )
        search = request.GET.get('search', None)
        self.check_object_permissions(request, module)
        datasets = Dataset.objects.filter(
            module__uuid=uuid
        )
        if search:
            datasets = datasets.filter(
                label__icontains=search
            )
        datasets = get_dataset_for_user(
            self.request.user,
            datasets
        )
        # order queryset
        datasets = self.sort_queryset(request, datasets)
        # set pagination
        paginator = Paginator(datasets, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                DatasetItemSerializer(
                    paginated_entities,
                    many=True
                ).data
            )
        return {
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'count': paginator.count,
            'results': output
        }, None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-dataset-detail',
                tags=[SEARCH_DATASET_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
                )],
                responses={
                    200: DetailedDatasetSerializer,
                    404: APIErrorSerializer
                }
            )
)
class DatasetDetail(ApiCache):
    """
    Find dataset detail

    Return detail of a dataset:
    - name
    - uuid
    - short_code
    - type
    - description
    - last_update
    - List of admin levels
    - Other external code types in dataset
    - bbox
    - max_zoom

    Requires Dataset UUID, can be retrieved from API search-dataset-list
    """
    permission_classes = [DatasetDetailAccessPermission]
    cache_model = Dataset

    def get_response_data(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset = get_object_or_404(
            Dataset, uuid=uuid, module__is_active=True
        )
        self.check_object_permissions(request, dataset)
        response_data = (
            DetailedDatasetSerializer(
                dataset,
                context={
                    'api_version': request.version,
                    'request': request
                }
            ).data
        )
        return response_data, None


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-dataset-hierarchical',
                tags=[SEARCH_ENTITY_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
                )],
                responses={
                    200: openapi.Schema(
                        description=(
                            'Hierarchical Entity Default Code'
                        ),
                        type=openapi.TYPE_OBJECT,
                        example=[{
                            'PAK_V1': [{
                                'PAK_0001_V1': [
                                    'PAK_0001_0001_V1',
                                    'PAK_0001_0002_V1',
                                ]}
                            ]
                        }]
                    ),
                    404: APIErrorSerializer
                }
            )
)
class DatasetEntityListHierarchical(ApiCache):
    """
    Find hierarchical of geographical entity in dataset

    Return hierarchical of unique code from geographical entity list \
    in dataset.

    Example response:
    ```
    [{
        'PAK_V1': [
            {
            'PAK_0001_V1': [
                'PAK_0001_0001_V1',
                'PAK_0001_0002_V1',
                ]
            }
        ]
    }]
    ```
    """
    permission_classes = [DatasetDetailAccessPermission]
    cache_model = Dataset

    def entities_code(self, parent_entity: GeographicalEntity,
                      max_privacy_level: int):
        codes = []
        entities = GeographicalEntity.objects.filter(
            parent=parent_entity,
            is_approved=True,
            is_latest=True,
            dataset=parent_entity.dataset,
            privacy_level__lte=max_privacy_level
        ).order_by('unique_code').defer('geometry').iterator()
        for entity in entities:
            if (
                GeographicalEntity.objects.filter(
                    parent=entity,
                    is_approved=True,
                    is_latest=True,
                    dataset=parent_entity.dataset,
                    privacy_level__lte=max_privacy_level
                ).exists()
            ):
                codes.append({
                    entity.ucode: self.entities_code(entity,
                                                     max_privacy_level)
                })
            else:
                codes.append(entity.ucode)
        return codes

    def get_response_data(self, request, *args, **kwargs):
        dataset_uuid = kwargs.get('uuid', None)
        entity_uuid = kwargs.get('concept_uuid', None)
        codes = []
        dataset = get_object_or_404(
            Dataset, uuid=dataset_uuid, module__is_active=True
        )
        self.check_object_permissions(request, dataset)
        # retrieve user privacy level for this dataset
        max_privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset
        )
        if max_privacy_level == 0:
            raise PermissionDenied(
                'You are not allowed to access this dataset'
            )
        try:
            ancestor = GeographicalEntity.objects.get(
                uuid=entity_uuid,
                dataset=dataset,
                is_approved=True,
                is_latest=True,
                privacy_level__lte=max_privacy_level
            )
        except ValidationError:
            raise Http404()

        codes.append({
            ancestor.ucode: self.entities_code(ancestor,
                                               max_privacy_level)
        })

        return codes, None


class DatasetExportFilters(object):

    map_filter_attributes = {
        'countries': 'country',
        'entity_types': 'type',
        'names': 'name',
        'ucodes': 'ucode',
        'revisions': 'revision',
        'levels': 'level',
        'valid_on': 'valid_from',
        'admin_level_names': 'admin_level_name',
        'sources': 'source',
        'privacy_levels': 'privacy_level',
        'search_text': 'search_text'
    }

    def get_filters(self, request):
        input_filters = request.data.get('filters', {})
        output_filters = {}
        error = None
        for attrib in self.map_filter_attributes:
            if attrib not in input_filters:
                continue
            output_filter_key = self.map_filter_attributes[attrib]
            filter_values = input_filters[attrib]
            if attrib == 'valid_on':
                # validate valid datetime format
                if filter_values:
                    dt_result = validate_datetime(filter_values)
                    if dt_result is not None:
                        output_filters[output_filter_key] = filter_values
                    else:
                        error = (
                            f'Invalid ISO datetime format: {filter_values}'
                        )
                        break
            elif filter_values and len(filter_values) > 0:
                output_filters[output_filter_key] = filter_values
        if error:
            return None, error
        return output_filters, None


class DatasetExportBase(DatasetExportFilters):

    def check_zoom_level(self, dataset: Dataset, zoom_level: int):
        return DatasetTilingConfig.objects.filter(
            dataset=dataset,
            zoom_level=zoom_level
        ).exists()

    def validate_request(
        self, dataset: Dataset, format,
        is_simplified_entities, simplification_zoom_level
    ):
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
            if not dataset.is_simplified:
                return Response(
                    status=400,
                    data={
                        'detail': (
                            'There is ongoing simplification process'
                            ' for the dataset!' if
                            dataset.simplification_sync_status ==
                            'syncing' else
                            'The dataset has out of sync simplified entities!'
                        )
                    }
                )
            if (
                not self.check_zoom_level(dataset, simplification_zoom_level)
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
        return None

    def submit_export_request(
        self, dataset: Dataset, format, user, is_simplified_entities,
        simplification_zoom_level, filters, source
    ):
        export_request = DatasetExportRequest.objects.create(
            dataset=dataset,
            format=format,
            submitted_on=timezone.now(),
            submitted_by=user,
            status=PENDING,
            status_text=str(ExportRequestStatusText.WAITING),
            is_simplified_entities=is_simplified_entities,
            simplification_zoom_level=simplification_zoom_level,
            filters=filters,
            source=source
        )
        celery_task = dataset_exporter.apply_async(
            (export_request.id,), queue='exporter'
        )
        export_request.task_id = celery_task.id
        export_request.save(update_fields=['task_id'])
        return export_request


class DatasetDownloader(
    APILoggingMixin, APIView, DatasetExportBase
):
    """
    Download dataset to several formats.

    Available formats:
    - GEOJSON
    - SHAPEFILE
    - TOPOJSON
    - KML
    - GEOPACKAGE

    The entities can be filtered by below attributes:
    - simplification_zoom_level (0-14)
    - countries: List of country e.g. ['Malawi', 'Zambia']
    - entity_types: List of entity type e.g. ['Country']
    - names: List of entity name e.g. ['Malawi', 'Zambia']
    - ucodes: List of entity ucodes e.g. ['DMC4_152_V1']
    - revisions: List of revision e.g. [1, 2]
    - levels: List of admin level e.g. [0, 1]
    - valid_on: Datetime when entities are valid, \
        e.g. '2014-12-05T12:30:45.123456-05:30'
    - admin_level_names: List of admin_level_name, e.g. ['Country']
    - sources: List of entity source
    - privacy_levels: List of privacy level, e.g. [1, 2]
    - search_text
    """
    permission_classes = [DatasetDetailAccessPermission]

    @swagger_auto_schema(
        operation_id='submit-download-dataset-job',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
        )],
        request_body=openapi.Schema(
            description='Download Job Request Body',
            type=openapi.TYPE_OBJECT,
            properties={
                'format': openapi.Schema(
                    title=(
                        'Format of exported product, '
                        f'one of {str(AVAILABLE_EXPORT_FORMAT_TYPES)}'
                    ),
                    type=openapi.TYPE_STRING
                ),
                'simplification_zoom_level': openapi.Schema(
                    title=(
                        'Zoom level that simplification was requested for. '
                        'Null if no simplification was requested.'
                    ),
                    type=openapi.TYPE_INTEGER
                ),
                'filters': openapi.Schema(
                    description='A dictionary if filters applied to the view',
                    type=openapi.TYPE_OBJECT,
                    properties=(
                        DatasetExportRequestStatusSerializer.
                        Meta.filters_schema_fields
                    )
                )
            }
        ),
        responses={
            200: DatasetExportRequestStatusSerializer,
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset = get_object_or_404(
            Dataset, uuid=uuid, module__is_active=True
        )
        filters, error = self.get_filters(request)
        if error:
            return Response(
                status=400,
                data={
                    'detail': error
                }
            )
        simplification_zoom_level = self.request.data.get(
            'simplification_zoom_level', None
        )
        is_simplified_entities = simplification_zoom_level is not None
        format = self.request.data.get(
            'format'
        )
        validation_response = self.validate_request(
            dataset, format, is_simplified_entities,
            simplification_zoom_level
        )
        if validation_response:
            return validation_response
        export_request = self.submit_export_request(
            dataset, format, self.request.user,
            is_simplified_entities, simplification_zoom_level,
            filters, 'api'
        )
        return Response(
            status=201,
            data=DatasetExportRequestStatusSerializer(export_request).data
        )


class DatasetDownloaderStatus(APILoggingMixin, APIView):
    """
    Fetch the download dataset job status.
    """
    permission_classes = [DatasetDetailAccessPermission]

    @swagger_auto_schema(
        operation_id='fetch-download-dataset-job-status',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'job_uuid', openapi.IN_QUERY,
            description=(
                'Job UUID'
            ),
            type=openapi.TYPE_STRING,
            required=True
        )],
        responses={
            200: DatasetExportRequestStatusSerializer,
            404: APIErrorSerializer
        }
    )
    def get(self, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        dataset = get_object_or_404(
            Dataset, uuid=uuid, module__is_active=True
        )
        job_uuid = self.request.GET.get('job_uuid')
        export_request = DatasetExportRequest.objects.filter(
            dataset=dataset,
            uuid=job_uuid
        ).first()
        if export_request is None:
            return Response(
                status=404,
                data={
                    'detail': (
                        f'There is no matching job request {job_uuid} '
                        f'in the dataset {dataset.name}'
                    )
                }
            )
        return Response(
            status=200,
            data=DatasetExportRequestStatusSerializer(export_request).data
        )
