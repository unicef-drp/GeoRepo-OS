import math
import datetime
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
    DatasetViewItemForUserSerializer
)
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_VIEW_TAG
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
class DatasetViewCentroid(ApiCache):
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
        resource = get_view_resource_from_view(dataset_view,
                                               user_privacy_level)
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
