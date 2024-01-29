import math
import os.path
import tempfile
import zipfile
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import (
    Http404,
    HttpResponse
)
from rest_framework.generics import get_object_or_404, GenericAPIView
from django.core.paginator import Paginator
from django.db.models import FilteredRelation, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from django.utils.text import slugify

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
    EntityId,
    Module
)
from georepo.models.entity import (
    MAIN_ENTITY_ID_LIST,
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID
)
from georepo.serializers.common import APIErrorSerializer
from georepo.serializers.dataset import (
    DatasetItemSerializer,
    DetailedDatasetSerializer
)
from georepo.utils.renderers import GeojsonRenderer, ShapefileRenderer
from georepo.utils.exporter_base import get_dataset_exported_file_name
from georepo.utils.unique_code import parse_unique_code
from georepo.utils.uuid_helper import get_uuid_value
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_DATASET_TAG,
    SEARCH_ENTITY_TAG,
    DOWNLOAD_DATA_BY_DATASET_TAG
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
        ).order_by('label')
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


class DatasetExportDownload(GenericAPIView):
    """
    Download dataset as given {format} in zip file

    Download zip file of requested format from dataset
    !DEPRECATED!
    """
    permission_classes = [DatasetDetailAccessPermission]
    renderer_classes = [GeojsonRenderer, ShapefileRenderer]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="Dataset UUID", type=openapi.TYPE_STRING
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[geojson, shapefile]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset: Dataset):
        format = self.request.GET.get('format', 'geojson')
        suffix = '.geojson' if format == 'geojson' else '.zip'
        results = []
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            is_latest=True
        )
        levels = entities.order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        for level in levels:
            exported_name = get_dataset_exported_file_name(level)
            file_path = os.path.join(
                str(dataset.uuid),
                exported_name
            ) + suffix
            if not os.path.exists(file_path):
                return [], None
            results.append(file_path)
        return results, None

    def get_output_names(self, dataset: Dataset, adm0_id: str = None):
        prefix_name = slugify(dataset.label).replace('-', '_')
        zip_file_name = f'{prefix_name}.zip'
        format = self.request.GET.get('format', 'geojson')
        if format == 'shapefile':
            zip_file_name = f'{prefix_name}_shp.zip'
        return prefix_name, zip_file_name

    @swagger_auto_schema(
                operation_id='download-dataset',
                tags=[DOWNLOAD_DATA_BY_DATASET_TAG],
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
        dataset = get_object_or_404(
            Dataset,
            uuid=uuid,
            module__is_active=True
        )
        self.check_object_permissions(request, dataset)
        result_list, adm0_list = self.get_exported_files(dataset)
        if len(result_list) == 0:
            raise Http404('The requested file does not exist')
        adm0_id = None
        if adm0_list:
            adm0_id = adm0_list[0] if len(adm0_list) == 1 else ''
        prefix_name, zip_file_name = self.get_output_names(dataset, adm0_id)
        with tempfile.SpooledTemporaryFile() as tmp_file:
            with zipfile.ZipFile(
                    tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:
                for result in result_list:
                    file_name = result.split('/')[-1]
                    archive.write(
                        result,
                        arcname=f'{prefix_name}_{file_name}'
                    )
            tmp_file.seek(0)
            response = HttpResponse(
                tmp_file.read(), content_type='application/x-zip-compressed'
            )
            response['Content-Disposition'] = (
                'attachment; filename="{}"'.format(
                    zip_file_name
                )
            )
            return response


class DatasetExportDownloadByLevel(DatasetExportDownload):
    """
    Download dataset as given {format} in zip file

    Download zip file of requested format from dataset
    !DEPRECATED!
    """

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="Dataset UUID",
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
        description='[geojson, shapefile]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset: Dataset):
        format = self.request.GET.get('format', 'geojson')
        # admin level
        admin_level = self.kwargs.get('admin_level')
        suffix = '.geojson' if format == 'geojson' else '.zip'
        results = []
        exported_name = get_dataset_exported_file_name(
            admin_level
        )
        file_path = os.path.join(
            str(dataset.uuid),
            exported_name
        ) + suffix
        if not os.path.exists(file_path):
            return [], None
        results.append(file_path)
        return results, None

    def get_output_names(self, dataset: Dataset, adm0_id: str = None):
        # admin level
        admin_level = self.kwargs.get('admin_level')
        prefix_name = slugify(dataset.label).replace('-', '_')
        zip_file_name = f'{prefix_name}_adm{admin_level}.zip'
        format = self.request.GET.get('format', 'geojson')
        if format == 'shapefile':
            zip_file_name = f'{prefix_name}_adm{admin_level}_shp.zip'
        return prefix_name, zip_file_name

    @swagger_auto_schema(
        operation_id='download-dataset-by-level',
        tags=[DOWNLOAD_DATA_BY_DATASET_TAG],
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
        return super(DatasetExportDownloadByLevel, self).get(
            request, *args, **kwargs
        )


class DatasetExportDownloadByCountry(DatasetExportDownload):
    """
    Download dataset as given {format} in zip file

    Download zip file of requested format from dataset
    !DEPRECATED!
    """
    renderer_classes = [GeojsonRenderer, ShapefileRenderer]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="Dataset UUID", type=openapi.TYPE_STRING
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
        description='[geojson, shapefile]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_adm0(self, dataset: Dataset):
        """Retrieve adm0 with id_type and id value, may return multiple"""
        id_type = self.kwargs.get('id_type', None)
        id_type = id_type.lower() if id_type else None
        id_value = self.kwargs.get('id', None)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            level=0
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
                    level=0
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

    def get_exported_files(self, dataset: Dataset):
        format = self.request.GET.get('format', 'geojson')
        suffix = '.geojson' if format == 'geojson' else '.zip'
        results = []
        adm0_list = self.get_adm0(dataset)
        if not adm0_list:
            return results, None
        added_ucodes = []
        for adm0 in adm0_list:
            if adm0.unique_code in added_ucodes:
                # skip if it's the same entity
                continue
            entities = GeographicalEntity.objects.filter(
                dataset=dataset,
                is_approved=True
            ).filter(
                Q(ancestor=adm0) |
                (Q(ancestor__isnull=True) & Q(id=adm0.id))
            )
            levels = entities.order_by('level').values_list(
                'level',
                flat=True
            ).distinct()
            for level in levels:
                exported_name = get_dataset_exported_file_name(
                    level,
                    adm0
                )
                file_path = os.path.join(
                    str(dataset.uuid),
                    exported_name
                ) + suffix
                if not os.path.exists(file_path):
                    return [], None
                results.append(file_path)
            added_ucodes.append(adm0.unique_code)
        return results, added_ucodes

    def get_output_names(self, dataset: Dataset, adm0_id: str = None):
        prefix_name = slugify(dataset.label).replace('-', '_')
        zip_file_name = (
            f'{prefix_name}_{adm0_id}.zip' if
            adm0_id else f'{prefix_name}.zip'
        )
        format = self.request.GET.get('format', 'geojson')
        if format == 'shapefile':
            zip_file_name = (
                f'{prefix_name}_{adm0_id}_shp.zip' if
                adm0_id else f'{prefix_name}_shp.zip'
            )
        return prefix_name, zip_file_name

    @swagger_auto_schema(
        operation_id='download-dataset-by-country',
        tags=[DOWNLOAD_DATA_BY_DATASET_TAG],
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
        return super(DatasetExportDownloadByCountry, self).get(
            request, *args, **kwargs
        )


class DatasetExportDownloadByCountryAndLevel(DatasetExportDownloadByCountry):
    """
    Download dataset as given {format} in zip file

    Download zip file of requested format from dataset
    !DEPRECATED!
    """
    renderer_classes = [GeojsonRenderer, ShapefileRenderer]

    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description="Dataset UUID", type=openapi.TYPE_STRING
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
        description='[geojson, shapefile]',
        type=openapi.TYPE_STRING,
        default='geojson',
        required=False
    )

    def get_exported_files(self, dataset: Dataset):
        # admin level
        admin_level = self.kwargs.get('admin_level', None)
        format = self.request.GET.get('format', 'geojson')
        suffix = '.geojson' if format == 'geojson' else '.zip'
        results = []
        adm0_list = self.get_adm0(dataset)
        if not adm0_list:
            return results, None
        added_ucodes = []
        for adm0 in adm0_list:
            if adm0.unique_code in added_ucodes:
                # skip if it's the same entity
                continue
            exported_name = get_dataset_exported_file_name(
                admin_level,
                adm0
            )
            file_path = os.path.join(
                str(dataset.uuid),
                exported_name
            ) + suffix
            if not os.path.exists(file_path):
                return [], None
            results.append(file_path)
            added_ucodes.append(adm0.unique_code)
        return results, added_ucodes

    def get_output_names(self, dataset: Dataset, adm0_id: str = None):
        # admin level
        admin_level = self.kwargs.get('admin_level', None)
        prefix_name = slugify(dataset.label).replace('-', '_')
        zip_file_name = (
            f'{prefix_name}_{adm0_id}_adm{admin_level}.zip' if adm0_id else
            f'{prefix_name}_adm{admin_level}.zip'
        )
        format = self.request.GET.get('format', 'geojson')
        if format == 'shapefile':
            zip_file_name = (
                f'{prefix_name}_{adm0_id}_adm{admin_level}_shp.zip' if
                adm0_id else f'{prefix_name}_adm{admin_level}_shp.zip'
            )
        return prefix_name, zip_file_name

    @swagger_auto_schema(
        operation_id='download-dataset-by-country-and-level',
        tags=[DOWNLOAD_DATA_BY_DATASET_TAG],
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
        return super(DatasetExportDownloadByCountryAndLevel, self).get(
            request, *args, **kwargs
        )


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
