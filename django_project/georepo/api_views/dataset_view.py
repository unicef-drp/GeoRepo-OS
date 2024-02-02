import math
import datetime
from rest_framework.views import APIView
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user
from django.contrib.sites.models import Site
from django.utils import timezone
from rest_framework.response import Response

from georepo.utils.permission import (
    DatasetDetailAccessPermission,
    DatasetViewDetailAccessPermission,
    get_dataset_views_for_user,
    get_view_permission_privacy_level
)
from georepo.api_views.api_cache import ApiCache
from georepo.models.dataset_view import (
    DatasetView,
    DATASET_VIEW_DATASET_TAG,
    DatasetViewResource
)
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.serializers.dataset_view import (
    DatasetViewItemSerializer,
    DatasetViewDetailSerializer,
    DatasetViewItemForUserSerializer,
    ExportRequestStatusSerializer
)
from georepo.models.base_task_request import PENDING
from georepo.models.dataset_tile_config import DatasetTilingConfig
from georepo.models.dataset_view_tile_config import DatasetViewTilingConfig
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_VIEW_TAG,
    DOWNLOAD_DATA_TAG
)
from georepo.utils.api_parameters import common_api_params
from georepo.utils.permission import (
    EXTERNAL_READ_VIEW_PERMISSION_LIST
)
from georepo.utils.dataset_view import (
    get_view_resource_from_view
)
from georepo.utils.azure_blob_storage import (
    StorageContainerClient,
    DirectoryClient
)
from georepo.models.export_request import (
    ExportRequest,
    AVAILABLE_EXPORT_FORMAT_TYPES,
    ExportRequestStatusText
)
from georepo.tasks.dataset_view import dataset_view_exporter
from georepo.utils.entity_query import validate_datetime
from georepo.serializers.common import APIErrorSerializer


class DatasetViewFetchResource(object):

    def get_dataset_view(self):
        uuid = self.kwargs.get('uuid', None)
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=uuid,
            dataset__module__is_active=True
        )
        self.check_object_permissions(self.request, dataset_view)
        return dataset_view

    def get_view_resource_obj(self):
        """
        Retrive view resource based on user permission
        """
        dataset_view = self.get_dataset_view()
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        return get_view_resource_from_view(dataset_view,
                                           user_privacy_level)


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
class DatasetViewDetail(ApiCache, DatasetViewFetchResource):
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
        dataset_view = self.get_dataset_view()
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


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-view-centroid',
                tags=[SEARCH_VIEW_TAG],
                manual_parameters=[],
                responses={
                    200: openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        title='View Centroid List',
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'level': openapi.Schema(
                                    title='Admin Level',
                                    type=openapi.TYPE_INTEGER
                                ),
                                'url': openapi.Schema(
                                    title=(
                                        'URL to download centroid in pbf file'
                                    ),
                                    type=openapi.TYPE_STRING
                                ),
                                'expired_on': openapi.Schema(
                                    title=(
                                        'Download URL expired on'
                                    ),
                                    type=openapi.TYPE_STRING
                                ),
                            }
                        )
                    )
                }
            )
)
class DatasetViewCentroid(ApiCache, DatasetViewFetchResource):
    """
    Fetch the URL to download centroid for each admin level.

    Fetch the URLs to the pbf file that contains centroid \
    of the entities in the view.
    The pbf file has following attributes:
    - c: concept_uuid
    - n: name
    - u: ucode

    Requires View UUID, can be retrieved from API search-view-list.
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    cache_model = DatasetView

    def get_download_url(self, file_path):
        download_link = None
        expired_on = None
        if settings.USE_AZURE:
            bc = StorageContainerClient.get_blob_client(blob=file_path)
            if bc.exists():
                # generate temporary url with sas token
                client = DirectoryClient(settings.AZURE_STORAGE,
                                         settings.AZURE_STORAGE_CONTAINER)
                download_link = client.generate_url_for_file(
                    file_path, settings.EXPORT_DATA_EXPIRY_IN_HOURS)
                expired_on = (
                    timezone.now() +
                    datetime.timedelta(
                        hours=settings.EXPORT_DATA_EXPIRY_IN_HOURS)
                )
            else:
                expired_on = None
        else:
            current_site = Site.objects.get_current()
            scheme = 'https://'
            domain = current_site.domain
            if not domain.endswith('/'):
                domain = domain + '/'
            download_link = (
                f'{scheme}{domain}{file_path}'
            )
            expired_on = None
        return download_link, expired_on

    def get_response_data(self, request, *args, **kwargs):
        resource = self.get_view_resource_obj()
        response_data = []
        if resource and resource.centroid_files:
            for centroid_file in resource.centroid_files:
                download_url, expired_on = self.get_download_url(
                    centroid_file['path'])
                if download_url:
                    response_data.append({
                        'level': centroid_file['level'],
                        'url': download_url,
                        'expired_on': expired_on
                    })
        return response_data, None


class DatasetViewExportBase(object):

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

    def validate_request(self,
                         dataset_view: DatasetView,
                         format,
                         is_simplified_entities,
                         simplification_zoom_level):
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
        return None

    def submit_export_request(self, dataset_view: DatasetView,
                              format, user, is_simplified_entities,
                              simplification_zoom_level, filters,
                              source):
        export_request = ExportRequest.objects.create(
            dataset_view=dataset_view,
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
        celery_task = dataset_view_exporter.apply_async(
            (export_request.id,), queue='exporter'
        )
        export_request.task_id = celery_task.id
        export_request.save(update_fields=['task_id'])
        return export_request


class DatasetViewDownloader(APIView, DatasetViewFetchResource,
                            DatasetViewExportBase):
    """
    Download dataset view to several formats.

    Available formats:
    - GEOJSON
    - SHAPEFILE
    - TOPOJSON
    - KML

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
    permission_classes = [DatasetViewDetailAccessPermission]
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

    def get_filters(self):
        input_filters = self.request.data.get('filters', {})
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


    @swagger_auto_schema(
        operation_id='submit-download-job',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
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
                        ExportRequestStatusSerializer.
                        Meta.filters_schema_fields
                    )
                )
            }
        ),
        responses={
            200: ExportRequestStatusSerializer,
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        filters, error = self.get_filters()
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
            dataset_view, format, is_simplified_entities,
            simplification_zoom_level
        )
        if validation_response:
            return validation_response
        export_request = self.submit_export_request(
            dataset_view, format, self.request.user,
            is_simplified_entities, simplification_zoom_level,
            filters, 'api'
        )
        return Response(
            status=201,
            data=ExportRequestStatusSerializer(export_request).data
        )


class DatasetViewDownloaderStatus(APIView, DatasetViewFetchResource):
    """
    Fetch the download view job status.
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    @swagger_auto_schema(
        operation_id='fetch-download-job-status',
        tags=[DOWNLOAD_DATA_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'job_uuid', openapi.IN_QUERY,
            description=(
                'Job UUID'
            ),
            type=openapi.TYPE_STRING,
            required=True
        )],
        responses={
            200: ExportRequestStatusSerializer,
            404: APIErrorSerializer
        }
    )
    def get(self, *args, **kwargs):
        dataset_view = self.get_dataset_view()
        job_uuid = self.request.GET.get('job_uuid')
        export_request = ExportRequest.objects.filter(
            dataset_view=dataset_view,
            uuid=job_uuid
        ).first()
        if export_request is None:
            return Response(
                status=404,
                data={
                    'detail': (
                        f'There is no matching job request {job_uuid} '
                        f'in the view {dataset_view.name}'
                    )
                }
            )
        return Response(
            status=200,
            data=ExportRequestStatusSerializer(export_request).data
        )
