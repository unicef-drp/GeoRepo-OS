import math
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import (
    Http404
)
from rest_framework.generics import get_object_or_404
from django.core.paginator import Paginator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator

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
from georepo.serializers.common import APIErrorSerializer
from georepo.serializers.dataset import (
    DatasetItemSerializer,
    DetailedDatasetSerializer
)
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_DATASET_TAG,
    SEARCH_ENTITY_TAG
)
from georepo.utils.api_parameters import common_api_params


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-dataset-list',
                tags=[SEARCH_DATASET_TAG],
                manual_parameters=[
                    openapi.Parameter(
                        'uuid', openapi.IN_PATH,
                        description="Module UUID", type=openapi.TYPE_STRING
                    ), *common_api_params
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
class DatasetList(ApiCache):
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

    def get_response_data(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid')
        page = int(request.GET.get('page', '1'))
        page_size = get_page_size(request)
        module = get_object_or_404(
            Module, uuid=uuid, is_active=True
        )
        self.check_object_permissions(request, module)
        datasets = Dataset.objects.filter(
            module__uuid=uuid
        ).order_by('-is_preferred', 'label')
        datasets = get_dataset_for_user(
            self.request.user,
            datasets
        )
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
