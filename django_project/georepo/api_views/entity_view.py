import math
import json
from rest_framework.views import APIView
from django.db import connection
from django.db.models.expressions import RawSQL
from django.db.models import FilteredRelation, Q
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from django.contrib.gis.geos import GEOSGeometry

from core.mixins import APILoggingMixin
from core.models.preferences import SitePreferences
from georepo.utils.permission import (
    DatasetViewDetailAccessPermission,
    get_view_permission_privacy_level
)
from georepo.api_views.entity import (
    FindEntityById,
    EntityListByAdminLevel,
    EntityListByAdminLevelAndUCode,
    EntityList,
    EntityListByUCode,
    FindEntityVersionsByConceptUCode,
    FindEntityVersionsByUCode,
    EntityGeometryFuzzySearch,
    EntityContainmentCheck,
    EntityTraverseHierarchyByUCode,
    EntityBatchSearchId,
    EntityBatchSearchIdStatus,
    EntityBatchSearchIdResult,
    EntityBatchGeocoding,
    EntityBatchGeocodingStatus,
    EntityBatchGeocodingResult,
    EntityListBoundingBox,
    FindEntityByUCode,
    FindEntityByCUCode
)
from georepo.models.dataset import Dataset
from georepo.models.entity import (
    MAIN_ENTITY_ID_LIST,
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    EntityId,
    GeographicalEntity,
    EntityType
)
from georepo.models.id_type import IdType
from georepo.models.dataset_view import DatasetView
from georepo.models.search_id_request import (
    SearchIdRequestType
)
from georepo.models.geocoding_request import (
    GeocodingRequestType
)
from georepo.serializers.common import APIErrorSerializer
from georepo.serializers.entity import (
    GeographicalEntitySerializer,
    SearchGeometrySerializer,
    FuzzySearchEntitySerializer,
    FindEntityByUCodeSerializer
)
from georepo.utils.unique_code import (
    parse_unique_code,
    get_unique_code
)
from georepo.utils.uuid_helper import get_uuid_value
from georepo.utils.geojson import validate_geojson
from georepo.api_views.api_collections import (
    SEARCH_VIEW_ENTITY_TAG,
    OPERATION_VIEW_ENTITY_TAG
)
from georepo.utils.api_parameters import (
    common_api_params,
    search_param,
    search_type_param
)
from georepo.utils.entity_query import (
    do_generate_fuzzy_query
)
from georepo.utils.url_helper import get_page_size


class DatasetViewDetailCheckPermission(object):

    def get_dataset_view_obj(self, request, uuid):
        """
        Check dataset_view obj permission and
        return max_privacy_level for read
        """
        dataset_view = get_object_or_404(
            DatasetView,
            uuid=uuid,
            dataset__module__is_active=True
        )
        self.check_object_permissions(request, dataset_view)
        # retrieve user privacy level for this dataset
        max_privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        if max_privacy_level == 0:
            raise PermissionDenied(
                'You are not allowed to '
                'access this view'
            )
        return dataset_view, max_privacy_level


class DatasetViewSearchBase(object):
    permission_classes = [DatasetViewDetailAccessPermission]
    # set cache_model
    cache_model = DatasetView
    # [Dataset, View]
    search_source = 'View'

    def get_response_data(self, request, *args, **kwargs):
        # dataset uuid
        uuid = kwargs.get('uuid', None)
        try:
            dataset_view = DatasetView.objects.select_related(
                'dataset',
                'dataset__module',
            ).get(
                uuid=uuid
            )
            if not dataset_view.dataset.module.is_active:
                raise Http404
            self.check_object_permissions(request, dataset_view)
            kwargs['uuid'] = str(dataset_view.dataset.uuid)
            kwargs['view_uuid'] = str(dataset_view.uuid)
        except DatasetView.DoesNotExist:
            raise Http404
        return super(DatasetViewSearchBase, self).get_response_data(
            request, *args, **kwargs
        )

    def get_admin_level_param(self):
        admin_level = None
        kwargs_adm_level = self.kwargs.get('admin_level', None)
        if kwargs_adm_level is not None:
            admin_level = kwargs_adm_level
        return admin_level

    def generate_response(self, entities, context=None):
        if entities is not None:
            # raw_sql to view to select id
            admin_level_param = self.get_admin_level_param()
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(self.kwargs.get('uuid')))
            if admin_level_param is not None:
                raw_sql = (
                    'SELECT id from "{view}" where level={admin_level}'
                ).format(
                    view=str(self.kwargs.get('uuid')),
                    admin_level=admin_level_param
                )
            # Query existing entities with uuids found in views
            entities = entities.filter(
                id__in=RawSQL(raw_sql, [])
            )
        return super(DatasetViewSearchBase, self).generate_response(
            entities, context)


class FindViewEntityById(DatasetViewSearchBase, FindEntityById):
    """
        Find geographical entities in view by one of ID

        Return geographical entity detail that has identifier {id}\
        with type {id_type}
        For {id_type} list can be retrieved from API id-type-list
        if timestamp is provided in query parameter, then API will filter \
        the result by that timestamp

        Example request:
        ```
        GET /search/view/{view_uuid}/entity/identifier/PCode/PAK/
        GET /search/view/{view_uuid}/entity/identifier/ucode/PAK_001_V1/
        GET /search/view/{view_uuid}/entity/identifier/
            ucode/PAK_001_V1/?timestamp=2023-03-06
        ```
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-id',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'id_type', openapi.IN_PATH,
            description=(
                'Entity ID Type; The list is available '
                'from API id-type-list'
            ),
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'id', openapi.IN_PATH,
            description=(
                'Entity ID Value; '
                'e.g. id_type=ucode, id=PAK_001_V1'
            ),
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'timestamp', openapi.IN_QUERY,
            description=(
                'Timestamp in ISO8601 or Epoch'
            ),
            type=openapi.TYPE_STRING,
            required=False
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                    GeographicalEntitySerializer.Meta.
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
                                GeographicalEntitySerializer.Meta.
                                swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(FindViewEntityById, self).get(
            request, *args, **kwargs
        )


class ViewEntityListByAdminLevel0(DatasetViewSearchBase,
                                  EntityListByAdminLevel):
    """
        List all entities at level 0 if the dataset is heirachical, \
            otherwise all entities

        List all entities at level 0 if the dataset is heirachical, \
            otherwise all entities

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-level-0',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByAdminLevel0, self).get(
            request, *args, **kwargs
        )

    def get_response_data(self, request, *args, **kwargs):
        kwargs['admin_level'] = 0
        return super(ViewEntityListByAdminLevel0, self).get_response_data(
            request, *args, **kwargs
        )


class ViewEntityListByAdminLevel(DatasetViewSearchBase,
                                 EntityListByAdminLevel):
    """
        Find geographical entities by level in view

        Retrieve geographical entities in view \
        with filter level={admin_level}

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-level',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'admin_level', openapi.IN_PATH,
            description=(
                'Admin level of the entity'
            ),
            type=openapi.TYPE_INTEGER
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByAdminLevel, self).get(
            request, *args, **kwargs
        )


class ViewEntityListByAdminLevelAndUCode(
        DatasetViewSearchBase,
        EntityListByAdminLevelAndUCode):
    """
        Find geographical entities by level and ancestor ucode in view

        Retrieve geographical entities in view \
        with filter level={admin_level} and parent ucode={ucode}

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-level-and-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'admin_level', openapi.IN_PATH,
            description=(
                'Admin level of the entity'
            ),
            type=openapi.TYPE_INTEGER
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description='Entity Root UCode',
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByAdminLevelAndUCode, self).get(
            request, *args, **kwargs
        )


class ViewEntityListByAdminLevelAndConceptUCode(
        DatasetViewSearchBase,
        EntityListByAdminLevelAndUCode):
    """
        Find geographical entities by level and ancestor concept ucode in view

        Retrieve geographical entities in view \
        with filter level={admin_level} and \
            ancestor concept_ucode={concept_ucode}

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-level-and-concept-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'admin_level', openapi.IN_PATH,
            description=(
                'Admin level of the entity'
            ),
            type=openapi.TYPE_INTEGER
        ), openapi.Parameter(
            'concept_ucode', openapi.IN_PATH,
            description='Entity Root Concept UCode',
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByAdminLevelAndConceptUCode, self).get(
            request, *args, **kwargs
        )


class ViewEntityListByEntityType(
        DatasetViewSearchBase,
        EntityList):
    """
        Find geographical entities by entity type in view

        Retrieve geographical entities in view \
        with filter type={entity_type}

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-type',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'entity_type', openapi.IN_PATH,
            description=(
                'Entity Type e.g. Country; '
                'The list is available from /api/v1/entity-type/'
                'Note that space should be replaced by underscore,'
                'e.g. Sub district -> Sub_district'
            ),
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByEntityType, self).get(
            request, *args, **kwargs
        )


class ViewEntityListByEntityTypeAndUcode(
        DatasetViewSearchBase,
        EntityListByUCode):
    """
        Find geographical entities by entity type and \
            root_entity ucode in view

        Retrieve geographical entities in view \
        with filter type={entity_type} and root_entity ucode={ucode}

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-by-type-and-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'entity_type', openapi.IN_PATH,
            description=(
                'Entity Type e.g. Country; '
                'The list is available from /api/v1/entity-type/'
                'Note that space should be replaced by underscore,'
                'e.g. Sub district -> Sub_district'
            ),
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description='Entity Root UCode',
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        ), search_param, search_type_param],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityListByEntityTypeAndUcode, self).get(
            request, *args, **kwargs
        )


class ViewFindEntityVersionsByConceptUCode(
        DatasetViewSearchBase,
        FindEntityVersionsByConceptUCode):
    """
    Find all revisions of geographical entities in view by Concept UCode

    Return geographical entity detail that has concept ucode {concept_ucode} \
        in view {uuid}.

    Example request:
    ```
    GET /search/view/{view_uuid}/entity/version/{concept_ucode}/
    GET /search/view/{view_uuid}/entity/version/
        {concept_ucode}/?timestamp=2014-12-05T12:30:45.123456-05:30
    ```
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-versions-by-concept-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'concept_ucode', openapi.IN_PATH,
            description=(
                'Entity Concept UCode'
            ),
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'timestamp', openapi.IN_QUERY,
            description=(
                'Timestamp in ISO8601 or Epoch'
            ),
            type=openapi.TYPE_STRING,
            required=False
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewFindEntityVersionsByConceptUCode, self).get(
            request, *args, **kwargs
        )


class ViewFindEntityVersionsByUCode(
        DatasetViewSearchBase,
        FindEntityVersionsByUCode):
    """
    Find all revisions of geographical entities in view by UCode

    Return geographical entity detail that has same concept uuid \
        with entity {ucode} in view {uuid}.

    Example request:
    ```
    GET /search/view/{view_uuid}/entity/version/{ucode}/
    GET /search/view/{view_uuid}/entity/version/
        {ucode}/?timestamp=2014-12-05T12:30:45.123456-05:30
    ```
    """

    @swagger_auto_schema(
        operation_id='search-view-entity-versions-by-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description=(
                'Entity UCode'
            ),
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'timestamp', openapi.IN_QUERY,
            description=(
                'Timestamp in ISO8601 or Epoch'
            ),
            type=openapi.TYPE_STRING,
            required=False
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewFindEntityVersionsByUCode, self).get(
            request, *args, **kwargs
        )


class ViewFindEntityFuzzySearch(
    APILoggingMixin, APIView, DatasetViewDetailCheckPermission
):
    """
    Find geographical entities by name

    Fuzzy search geographical entity by {search_text}

    Example request:
    ```
    GET /search/view/{uuid}/entity/PAK/?is_latest=True
    ```
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    def get_trigram_similarity(self):
        # fetch from site preferences
        return SitePreferences.preferences().search_similarity

    def sanitize_search_text(self, search_text):
        """
        sanitize the search text
        """
        # strip null characters
        search_text = search_text.replace('\x00', '')
        return search_text

    def do_run_sql_query(self, view: DatasetView, search_text: str,
                         max_privacy_level: int,
                         page: int, page_size: int,
                         admin_level: int = None):
        fuzzy_query = do_generate_fuzzy_query(
            view, search_text, max_privacy_level,
            page, page_size, admin_level
        )
        rows = []
        with connection.cursor() as cursor:
            set_similarity_sql = (
                """set pg_trgm.word_similarity_threshold=%s"""
            )
            cursor.execute(set_similarity_sql,
                           [self.get_trigram_similarity()])
            cursor.execute(fuzzy_query['sql'], fuzzy_query['query_values'])
            _rows = cursor.fetchall()
            for _row in _rows:
                _data = {}
                for i in range(len(fuzzy_query['select_keys'])):
                    key = fuzzy_query['select_keys'][i]
                    val = _row[i]
                    _data[key] = val
                rows.append(_data)
            cursor.execute(fuzzy_query['count_sql'],
                           fuzzy_query['count_query_values'])
            count_row = cursor.fetchone()[0]
        return rows, count_row, fuzzy_query

    @swagger_auto_schema(
        operation_id='search-view-entity-by-name',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'search_text', openapi.IN_PATH,
            description='search text',
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'admin_level', openapi.IN_QUERY,
            description='Filter by admin level',
            type=openapi.TYPE_INTEGER
        ), *common_api_params
        ],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                FuzzySearchEntitySerializer.Meta.
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
                            FuzzySearchEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        search_text = kwargs.get('search_text', '')
        search_text = self.sanitize_search_text(search_text)
        # search in admin_level
        admin_level = self.request.GET.get('admin_level', None)
        # pagination parameter
        page = int(self.request.GET.get('page', '1'))
        page_size = get_page_size(self.request)
        rows, count_row, fuzzy_query = self.do_run_sql_query(
            view, search_text, max_privacy_level, page, page_size,
            admin_level
        )
        total_page = math.ceil(count_row / page_size)
        if page > total_page:
            output = []
        else:
            output = FuzzySearchEntitySerializer(
                rows,
                many=True,
                context={
                    'max_level': fuzzy_query['max_level'],
                    'ids': fuzzy_query['ids'],
                    'names': fuzzy_query['names_max_idx']
                }
            ).data
        return Response(data={
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'count': count_row,
            'results': output
        })


class ViewFindEntityGeometryFuzzySearch(
        DatasetViewSearchBase,
        EntityGeometryFuzzySearch):
    """
    Find closest geographical entities

    Search top 10 Geographical Entity that has closest match with \
        given geometry
    If {is_latest} is provided, the API will only search \
    for entity with {is_latest} (default is True)

    Example request:
    ```
    POST /search/view/{uuid}/entity/geometry/?is_latest=True
    Request Content-type: application/json
    Request Body: Geojson
    ```
    """

    def generate_query(
            self,
            geom,
            is_latest,
            levels,
            dataset_uuid,
            max_privacy_level):
        view_uuid = self.kwargs.get('uuid', None)
        simplified_input = geom.simplify(self.get_simplify_tolerance()).ewkt
        query_values = [
            simplified_input,
            simplified_input,
            max_privacy_level
        ]
        subquery_sql = (
            'SELECT gg.*, parent_0.label as country, '
            'ST_HausdorffDistance(gg.geometry, %s) '
            'AS similarity '
            'FROM "{}" gg '
            'left join georepo_geographicalentity parent_0 on ( '
            '    parent_0.id = gg.ancestor_id '
            ') '
            'WHERE gg.is_approved AND ST_Intersects(gg.geometry, %s) AND '
            'gg.privacy_level<=%s'
        ).format(str(view_uuid))
        conditions = []
        if is_latest is not None:
            conditions.append('gg.is_latest=%s')
            query_values.append(is_latest)
        if levels:
            conditions.append('gg.level IN %s')
            query_values.append(tuple(levels))
        if conditions:
            subquery_sql = (
                subquery_sql + 'AND ' + ' AND '.join(conditions)
            )
        query = (
            'SELECT search.id, search.label, search.uuid_revision,'
            'search.type_id, '
            'search.level, search.dataset_id, search.country, '
            'search.similarity '
            'FROM (' +
            subquery_sql +
            ') as search '
            'ORDER BY search.similarity '
            'LIMIT 10'
        )
        return query, query_values

    @swagger_auto_schema(
        operation_id='search-view-entity-by-geometry',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'admin_level', openapi.IN_QUERY,
            description='Admin level. Example: 0',
            type=openapi.TYPE_INTEGER,
            required=False
        ), openapi.Parameter(
            'is_latest', openapi.IN_QUERY,
            description='True to search for latest entity only',
            type=openapi.TYPE_BOOLEAN,
            default=True,
            required=False
        ), openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        request_body=openapi.Schema(
            description='Geometry data (SRID 4326) in geojson format',
            type=openapi.TYPE_STRING
        ),
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                SearchGeometrySerializer.Meta.
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
                            SearchGeometrySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        uuid = kwargs.get('uuid', None)
        try:
            dataset_view = DatasetView.objects.get(
                uuid=uuid
            )
            self.check_object_permissions(request, dataset_view)
            kwargs['uuid'] = str(dataset_view.dataset.uuid)
            kwargs['view_uuid'] = str(dataset_view.uuid)
        except DatasetView.DoesNotExist:
            raise Http404
        return super(ViewFindEntityGeometryFuzzySearch, self).post(
            request, *args, **kwargs
        )


class ViewEntityBoundingBox(
    APILoggingMixin, APIView, DatasetViewDetailCheckPermission
):
    """
    Find bounding box of geographical entity

    Search Geographical Entity by id_type and its identifier value \
    and return its bounding box

    Example usage:
    id_type=PCode, id=PAK
    ```
    GET /operation/view/{uuid}/bbox/PCode/PAK/
    ```
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='View UUID',
        type=openapi.TYPE_STRING
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'Entity ID Type; The list is available from '
            '/api/v1/id-type/. '
            'Example: PCode'
        ),
        type=openapi.TYPE_STRING
    )
    id_param = openapi.Parameter(
        'id', openapi.IN_PATH,
        description=(
            'ID value of the Geographical Entity. '
            'Example: PAK'
        ),
        type=openapi.TYPE_STRING
    )

    @swagger_auto_schema(
        operation_id='operation-view-bbox',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[uuid_param, id_type_param, id_param],
        responses={
            200: openapi.Schema(
                description='Bounding Box',
                type=openapi.TYPE_OBJECT,
                example='[-121.5, 47.25, -120.4, 47.8]'
            ),
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        dataset_view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        req_label = kwargs.get('id_type', '').lower()
        req_id = kwargs.get('id', '')
        geom = None
        if req_label in MAIN_ENTITY_ID_LIST:
            entity = GeographicalEntity.objects.filter(
                is_approved=True,
                dataset=dataset_view.dataset,
                privacy_level__lte=max_privacy_level
            )
            # Query existing entity with uuids found in views
            entity = entity.filter(
                id__in=RawSQL(raw_sql, [])
            )
            if req_label == UUID_ENTITY_ID:
                uuid_val = get_uuid_value(req_id)
                entity = entity.filter(
                    uuid_revision=uuid_val
                )
            elif req_label == CONCEPT_UUID_ENTITY_ID:
                uuid_val = get_uuid_value(req_id)
                entity = entity.filter(
                    uuid=uuid_val
                )
            elif req_label == CODE_ENTITY_ID:
                entity = entity.filter(
                    internal_code=req_id
                )
            elif req_label == UCODE_ENTITY_ID:
                try:
                    ucode, version = parse_unique_code(req_id)
                except ValueError:
                    return Response(
                        status=400,
                        data={
                            'detail': f'Invalid Unique Code {req_id}'
                        }
                    )
                entity = entity.filter(
                    unique_code=ucode,
                    unique_code_version=version
                )
            elif req_label == CONCEPT_UCODE_ENTITY_ID:
                entity = entity.filter(
                    concept_ucode=req_id
                )
            entity = entity.last()
            if entity:
                geom = entity.geometry
        else:
            entity_id = EntityId.objects.filter(
                code__name__iexact=req_label,
                value=req_id,
                geographical_entity__is_approved=True,
                geographical_entity__dataset=dataset_view.dataset,
                geographical_entity__privacy_level__lte=max_privacy_level
            )
            # Query existing entity with uuids found in views
            entity_id = entity_id.filter(
                geographical_entity__id__in=RawSQL(raw_sql, [])
            )
            entity_id = entity_id.select_related(
                'geographical_entity'
            ).order_by('geographical_entity__id').last()
            if entity_id:
                geom = entity_id.geographical_entity.geometry
        if not geom:
            raise Http404('No GeographicalEntity matches the given query.')
        return Response(
            geom.extent
        )


class ViewEntityListBoundingBox(
    EntityListBoundingBox, DatasetViewDetailCheckPermission
):
    """
    Find bounding box of geographical entities

    Search Geographical Entity by id_type and its identifier values \
    and return its bounding box. id_type can be ucode or concept_uuid.

    Example usage:
    id_type=ucode
    ```
    POST /operation/view/{uuid}/bbox/ucode/

    Request body:
        ["PAK_V1", "IND_V1"]
    ```
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='View UUID',
        type=openapi.TYPE_STRING
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'Entity ID Type; ucode or concept_uuid. '
            'Example: ucode'
        ),
        type=openapi.TYPE_STRING
    )

    def _get_entities_query(self, request, kwargs):
        dataset_view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))

        entities = GeographicalEntity.objects.filter(
            is_approved=True,
            dataset=dataset_view.dataset,
            privacy_level__lte=max_privacy_level
        )
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        return entities

    @swagger_auto_schema(
        operation_id='operation-view-bbox-post',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[uuid_param, id_type_param],
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            example=["PAK_V1", "IND_V1"]
        ),
        responses={
            200: openapi.Schema(
                description='Bounding Box',
                type=openapi.TYPE_OBJECT,
                example='[-121.5, 47.25, -120.4, 47.8]'
            ),
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super(ViewEntityListBoundingBox, self).post(
            request, *args, **kwargs
        )


class ViewEntityContainmentCheck(EntityContainmentCheck,
                                 DatasetViewDetailCheckPermission):
    """
    Find geographical entities using spatial query

    Given Geojson data in the payload, find the identifier value \
        of {id_type} from Geographical Entity in the view\
        using below {spatial_query}:
    - ST_Intersects
    - ST_Within
    - ST_Within(ST_Centroid)
    - ST_DWithin (requires {distance})

    The search can be filtered by {entity_type} or {admin_level}\
        in query parameters.
    The result will be returned in the properties of the feature.
    Note that if no {entity_type}/{admin_level} is provided, then\
        the API will return hierarchical data.

    Example request:
    ```
    POST /operation/view/{uuid}/containment-check/
        ST_Intersects/0/ucode/?admin_level=0
    Request Content-type: application/json
    Request Body: Geojson
    ```
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='View UUID',
        type=openapi.TYPE_STRING
    )
    squery_param = openapi.Parameter(
        'spatial_query', openapi.IN_PATH,
        description='Spatial Query, e.g. ST_Intersects',
        type=openapi.TYPE_STRING
    )
    squeryd_param = openapi.Parameter(
        'distance', openapi.IN_PATH,
        description='Distance for ST_DWithin',
        type=openapi.TYPE_NUMBER,
        default=0
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'ID Type; The list is available from '
            'id-type-list API. Example: PCode'
        ),
        type=openapi.TYPE_STRING
    )
    geojson_body = openapi.Schema(
        description='Geometry data (SRID 4326) in geojson format',
        type=openapi.TYPE_STRING
    )
    entity_type_param = openapi.Parameter(
        'entity_type', openapi.IN_QUERY,
        description=(
            'Entity Type e.g. Country; '
            'The list is available from /api/v1/entity-type/'
            'Note that space should be replaced by underscore,'
            'e.g. Sub district -> Sub_district'
        ),
        type=openapi.TYPE_STRING
    )
    admin_level_param = openapi.Parameter(
        'admin_level', openapi.IN_QUERY,
        description=(
            'Admin level (Optional). Example: 0'
        ),
        type=openapi.TYPE_INTEGER
    )

    def get_id_value(self, id_type, results, is_hierarchical, dataset_view,
                     max_privacy_level):
        if not results:
            return []
        idx = 0
        if isinstance(id_type, IdType):
            idx = 0
        elif id_type == CONCEPT_UCODE_ENTITY_ID:
            idx = 4
        elif id_type == CODE_ENTITY_ID:
            idx = 3
        elif id_type == UUID_ENTITY_ID:
            idx = 2
        elif id_type == UCODE_ENTITY_ID:
            idx = 1
        if is_hierarchical:
            hierarchical_list = []
            id_idx = 1 if isinstance(id_type, IdType) else 0
            for result in results:
                geo_id = result[id_idx]
                id_key = result[idx]
                if not id_key:
                    continue
                hierarchy = {
                    str(id_key): self.entities_code(
                        geo_id,
                        id_type,
                        dataset_view,
                        max_privacy_level
                    )
                }
                hierarchical_list.append(
                    hierarchy
                )
            return hierarchical_list
        return [str(row[idx]) for row in results]

    def do_run_query(
            self,
            return_type: str,
            id_type: IdType | str,
            dataset: Dataset,
            dataset_view: DatasetView,
            spatial_query: str,
            dwithin_distance: int,
            geom: GEOSGeometry,
            max_privacy_level,
            admin_level: str = None,
            entity_type: EntityType = None) -> list:
        query_values = [
            dataset.id
        ]
        query = (
            'SELECT ' + ('gi.value, ' if isinstance(id_type, IdType) else '')
        )
        query = (
            query +
            "gg.id, gg.unique_code || '_V' || CASE WHEN "
            'gg.unique_code_version IS NULL THEN 1 ELSE '
            'gg.unique_code_version END, '
            'gg.uuid, gg.internal_code, gg.concept_ucode '
            'FROM georepo_geographicalentity gg '
        )
        if isinstance(id_type, IdType):
            # should query from EntityId
            query = (
                query + 'LEFT JOIN georepo_entityid gi '
                '  ON gi.geographical_entity_id = gg.id '
                'LEFT JOIN georepo_idtype gc '
                '  ON gi.code_id = gc.id '
            )
            query_values.append(return_type)
        query = (
            query +
            'INNER JOIN georepo_entitytype ge '
            '  ON gg.type_id = ge.id '
            'WHERE gg.dataset_id = %s AND ' +
            ('gc.name ilike %s AND ' if isinstance(id_type, IdType) else '')
        )

        if entity_type is None and admin_level is None:
            # search only in level 0 and return hierarchical
            query = (
                query + 'gg.level = 0 AND '
            )
        elif entity_type is not None:
            query = (
                query + 'ge.id = %s AND '
            )
            query_values.append(entity_type.id)
        else:
            query = (
                query + 'gg.level = %s AND '
            )
            query_values.append(admin_level)
        query_values.append(max_privacy_level)
        query_values.append(geom.ewkt)
        if spatial_query == 'ST_Intersects':
            spatial_params = 'ST_Intersects(%s, gg.geometry)'
        elif spatial_query == 'ST_Within':
            spatial_params = 'ST_Within(%s, gg.geometry)'
        elif spatial_query == 'ST_Within(ST_Centroid)':
            spatial_params = 'ST_Within(ST_Centroid(%s), gg.geometry)'
        elif spatial_query == 'ST_DWithin':
            spatial_params = 'ST_DWithin(%s, gg.geometry, %s)'
            query_values.append(dwithin_distance)
        view_sql = (
            'gg.id IN (SELECT id from "{}") AND '
        ).format(str(dataset_view.uuid))
        query = (
            query +
            'gg.is_approved=true AND gg.privacy_level<=%s AND ' +
            view_sql +
            f'{ spatial_params } '
        )
        if isinstance(id_type, IdType):
            query = (
                query +
                'GROUP BY gi.value, gg.id '
                'ORDER BY gi.value'
            )
        else:
            query = (
                query +
                'GROUP BY gg.id '
                'ORDER BY gg.id'
            )
        rows = []
        with connection.cursor() as cursor:
            cursor.execute(query, query_values)
            rows = cursor.fetchall()
        return [row for row in rows]

    def entities_code(self, parent_entity_id, id_type, dataset_view,
                      max_privacy_level):
        codes = []
        # initial fields to select
        values = [
            'id', 'internal_code', 'unique_code', 'uuid',
            'uuid_revision', 'unique_code_version', 'concept_ucode'
        ]
        entities = GeographicalEntity.objects.filter(
            parent__id=parent_entity_id,
            is_approved=True,
            is_latest=True,
            privacy_level__lte=max_privacy_level
        ).order_by('id')
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        # Query existing entities with uuids found in views
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        if isinstance(id_type, IdType):
            annotations = {
                'selected_id': FilteredRelation(
                    'entity_ids',
                    condition=Q(entity_ids__code__id=id_type.id)
                )
            }
            entities = entities.annotate(**annotations)
            values.append('selected_id__value')
        entities = entities.values(*values).iterator()
        for entity in entities:
            key = None
            entity_id = entity.get('id', None)
            if isinstance(id_type, IdType):
                key = entity.get('selected_id__value', None)
            elif id_type == UUID_ENTITY_ID:
                key = entity.get('uuid_revision', None)
            elif id_type == CONCEPT_UUID_ENTITY_ID:
                key = entity.get('uuid', None)
            elif id_type == CODE_ENTITY_ID:
                key = entity.get('internal_code', None)
            elif id_type == CONCEPT_UCODE_ENTITY_ID:
                key = entity.get('concept_ucode', None)
            elif id_type == UCODE_ENTITY_ID:
                key_1 = entity.get('unique_code', None)
                key_2 = entity.get('unique_code_version', 1)
                if key_1:
                    key = get_unique_code(key_1, key_2)
            if not key or not entity_id:
                continue
            count_child_sql = (
                'SELECT count(*) '
                'FROM "{}" gg '
                'INNER JOIN georepo_geographicalentity parent '
                '  ON parent.id=gg.parent_id '
                'WHERE parent.id=%s AND gg.is_approved=true '
                'AND gg.privacy_level<=%s'
            ).format(str(dataset_view.uuid))
            with connection.cursor() as cursor:
                cursor.execute(count_child_sql,
                               [entity['id'], max_privacy_level])
                total_child_count = cursor.fetchone()[0]
            if total_child_count > 0:
                codes.append({
                    str(key): self.entities_code(
                        entity_id,
                        id_type,
                        dataset_view,
                        max_privacy_level
                    )
                })
            else:
                codes.append(str(key))
        return codes

    @swagger_auto_schema(
        operation_id='operation-view-containment-check',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[
            uuid_param,
            squery_param,
            squeryd_param,
            id_type_param,
            entity_type_param,
            admin_level_param
        ],
        request_body=geojson_body,
        responses={
            200: geojson_body,
            400: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        dataset_view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        spatial_query = kwargs.get('spatial_query', None)
        if not spatial_query or not self.validate_query_type(spatial_query):
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid Spatial Query.'
                }).data
            )
        dwithin_distance = kwargs.get('distance', None)
        if (spatial_query == 'ST_DWithin' and
                dwithin_distance is None):
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid Distance in DWithin Spatial Query.'
                }).data
            )
        return_type = kwargs.get('id_type', None)
        return_type = return_type.lower() if return_type else None
        id_type = self.validate_return_type(return_type)
        if not id_type:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid Type.'
                }).data
            )
        level_type = request.GET.get('entity_type', None)
        valid_level_type, entity_type = self.validate_level_type(level_type)
        if not valid_level_type:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Invalid Entity Type: {level_type}.'
                }).data
            )
        admin_level = request.GET.get('admin_level', None)
        geojson = request.data
        if not validate_geojson(geojson):
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid Geojson Data.'
                }).data
            )
        is_hierarchical = level_type is None and admin_level is None
        if geojson['type'] == 'Feature':
            results = self.do_run_query(
                        return_type,
                        id_type,
                        dataset_view.dataset,
                        dataset_view,
                        spatial_query,
                        dwithin_distance,
                        GEOSGeometry(
                            json.dumps(geojson['geometry']), srid=4326
                        ),
                        max_privacy_level,
                        admin_level,
                        entity_type
                    )
            if results:
                return_type = kwargs.get('id_type', None)
                if 'properties' not in geojson:
                    geojson['properties'] = {}
                geojson['properties'][return_type] = (
                    self.get_id_value(
                        id_type,
                        results,
                        is_hierarchical,
                        dataset_view,
                        max_privacy_level
                    )
                )
        elif geojson['type'] == 'FeatureCollection':
            for idx, feature in enumerate(geojson['features']):
                results = self.do_run_query(
                            return_type,
                            id_type,
                            dataset_view.dataset,
                            dataset_view,
                            spatial_query,
                            dwithin_distance,
                            GEOSGeometry(
                                json.dumps(feature['geometry']), srid=4326
                            ),
                            max_privacy_level,
                            admin_level,
                            entity_type
                        )
                if results:
                    return_type = kwargs.get('id_type', None)
                    if 'properties' not in feature:
                        feature['properties'] = {}
                    feature['properties'][return_type] = (
                        self.get_id_value(
                            id_type,
                            results,
                            is_hierarchical,
                            dataset_view,
                            max_privacy_level
                        )
                    )
        return Response(
            geojson
        )


class ViewEntityTraverseHierarchyByUCode(
        DatasetViewSearchBase,
        EntityTraverseHierarchyByUCode,
        DatasetViewDetailCheckPermission):
    """
        Find parent from geographical entity with UCode

        Retrieve parent from Geographical Entity with {ucode} \
        in view

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """
    enable_search_text = False
    traverse_direction = 'up'

    def find_child(self, kwargs, dataset, ucode, version, max_privacy_level):
        # raw_sql to view to select id
        dataset_view_uuid = kwargs.get('view_uuid', None)
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view_uuid))
        child = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            unique_code=ucode,
            unique_code_version=version,
            privacy_level__lte=max_privacy_level
        ).filter(
            id__in=RawSQL(raw_sql, [])
        )
        return child.values('parent__id', 'parent__level').first()

    def find_parent(self, kwargs, dataset, ucode, version, max_privacy_level):
        # raw_sql to view to select id
        dataset_view_uuid = kwargs.get('view_uuid', None)
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view_uuid))
        parent = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            unique_code=ucode,
            unique_code_version=version,
            privacy_level__lte=max_privacy_level
        ).filter(
            id__in=RawSQL(raw_sql, [])
        ).first()
        return parent

    @swagger_auto_schema(
        operation_id='search-view-entity-parents-by-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description='Entity UCode',
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityTraverseHierarchyByUCode, self).get(
            request, *args, **kwargs
        )


class ViewEntityTraverseChildrenHierarchyByUCode(
        ViewEntityTraverseHierarchyByUCode):
    """
        Find children from geographical entity with UCode

        Retrieve children from geographical entity with {ucode} \
        in view

        For every entity, return below details:
        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """
    traverse_direction = 'down'

    @swagger_auto_schema(
        operation_id='search-view-entity-children-by-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description='Entity UCode',
            type=openapi.TYPE_STRING
        ), *common_api_params, openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
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
                        title='List of geographical entity',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_OBJECT,
                            properties=(
                                GeographicalEntitySerializer.Meta.
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
                            GeographicalEntitySerializer.Meta.
                            swagger_schema_fields['example']
                        )
                    ]
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityTraverseChildrenHierarchyByUCode, self).get(
            request, *args, **kwargs
        )


class ViewEntityBatchSearchId(
    EntityBatchSearchId, DatasetViewDetailCheckPermission
):
    """
    Batch search to find geographical entities in view by one of ID

    The search will be done in background and the result can be retrieved using
    API batch-result-search-view-by-id.
    For input_type and return_type can be retrieved from API id-type-list.
    If return_type is empty, then the output will be full entity detail.

    Example request:
    ```
    POST /search/view/{view_uuid}/batch/identifier/PCode/
    Request Body: [ "PAK", "MWI" ]
        ```
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET_VIEW
    status_url = 'v1:batch-status-search-view-by-id'

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='batch-search-view-by-id',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='View UUID', type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'input_type', openapi.IN_PATH,
                description=(
                    'Input ID Type; The list is available from '
                    'id-type-list API. Example: PCode'
                ),
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'return_type', openapi.IN_QUERY,
                description=(
                    'Return ID Type; The list is available from '
                    'id-type-list API. '
                    'Default to be empty and return all entity details.'
                ),
                type=openapi.TYPE_STRING
            )
        ],
        request_body=openapi.Schema(
            description='JSON List of Entity ID',
            type=openapi.TYPE_STRING
        ),
        responses={
            200: openapi.Schema(
                title='Batch Task Item',
                type=openapi.TYPE_OBJECT,
                properties={
                    'request_id': openapi.Schema(
                        title='Task Request ID',
                        type=openapi.TYPE_STRING
                    ),
                    'status_url': openapi.Schema(
                        title='URL to Batch Task Status API',
                        type=openapi.TYPE_STRING
                    ),
                },
                example={
                    'request_id': 'af9c24a0-02cf-4a12-beb2-fac126a9c709',
                    'status_url': (
                        '{base_url}/api/v1/search/view/'
                        'cd20c26b-ac26-47c3-8b73-a998cb1efff7/batch/result/'
                        'af9c24a0-02cf-4a12-beb2-fac126a9c709/'
                    )
                }
            ),
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super(ViewEntityBatchSearchId, self).post(
            request, *args, **kwargs
        )


class ViewEntityBatchGeocoding(
    EntityBatchGeocoding, DatasetViewDetailCheckPermission
):
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = GeocodingRequestType.DATASET_VIEW
    status_url = 'v1:check-status-batch-geocoding'
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='View UUID',
        type=openapi.TYPE_STRING
    )
    squery_param = openapi.Parameter(
        'spatial_query', openapi.IN_PATH,
        description=(
            'Spatial Query, e.g. ST_Intersects, ST_Within, '
            'ST_Within(ST_Centroid), ST_DWithin'
        ),
        type=openapi.TYPE_STRING
    )
    squeryd_param = openapi.Parameter(
        'distance', openapi.IN_PATH,
        description='Distance for ST_DWithin',
        type=openapi.TYPE_NUMBER,
        default=0
    )
    admin_level_param = openapi.Parameter(
        'admin_level', openapi.IN_PATH,
        description=(
            'Admin level. Example: 0'
        ),
        type=openapi.TYPE_INTEGER
    )
    id_type_param = openapi.Parameter(
        'id_type', openapi.IN_PATH,
        description=(
            'ID Type; The list is available from '
            'id-type-list API. Example: PCode'
        ),
        type=openapi.TYPE_STRING
    )
    find_nearest_param = openapi.Parameter(
        'find_nearest', openapi.IN_QUERY,
        description=(
            'Return the nearest entity when the input geometry '
            'does not fall into any of the boundaries. Default to False'
        ),
        default=False,
        type=openapi.TYPE_BOOLEAN
    )
    post_body = openapi.Parameter(
        'file', openapi.IN_FORM,
        description=(
            'Geometry data (SRID 4326) in one of the format: '
            'geojson, shapefile, GPKG'
        ),
        type=openapi.TYPE_FILE
    )

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='batch-geocoding',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[
            uuid_param,
            squery_param,
            squeryd_param,
            admin_level_param,
            id_type_param,
            find_nearest_param,
            post_body
        ],
        # request_body=post_body,
        responses={
            200: openapi.Schema(
                title='Batch Task Item',
                type=openapi.TYPE_OBJECT,
                properties={
                    'request_id': openapi.Schema(
                        title='Task Request ID',
                        type=openapi.TYPE_STRING
                    ),
                    'status_url': openapi.Schema(
                        title='URL to Batch Task Status API',
                        type=openapi.TYPE_STRING
                    ),
                },
                example={
                    'request_id': 'af9c24a0-02cf-4a12-beb2-fac126a9c709',
                    'status_url': (
                        '{base_url}/api/v1/operation/view/'
                        'cd20c26b-ac26-47c3-8b73-a998cb1efff7/'
                        'batch-containment-check/status/'
                        'af9c24a0-02cf-4a12-beb2-fac126a9c709/'
                    )
                }
            ),
            400: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super(ViewEntityBatchGeocoding, self).post(
            request, *args, **kwargs
        )


class ViewEntityBatchSearchIdStatus(
    EntityBatchSearchIdStatus, DatasetViewDetailCheckPermission
):
    """
    Check status of batch search by id

    Task is completed when status is one of DONE, ERROR, or CANCELLED.
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET_VIEW
    result_url = 'v1:batch-result-search-view-by-id'

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='batch-status-search-view-by-id',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='View UUID', type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'request_id', openapi.IN_PATH,
                description=(
                    'Task Request ID'
                ),
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Schema(
                title='Batch Task Status',
                type=openapi.TYPE_OBJECT,
                properties={
                    'request_id': openapi.Schema(
                        title='Request ID',
                        type=openapi.TYPE_STRING
                    ),
                    'status': openapi.Schema(
                        title=(
                            'Task Status. One of PENDING, PROCESSING, DONE, '
                            'ERROR, CANCELLED'
                        ),
                        type=openapi.TYPE_STRING
                    ),
                    'error': openapi.Schema(
                        title=(
                            'Error when batch job is failed'
                        ),
                        type=openapi.TYPE_STRING
                    ),
                    'output_url': openapi.Schema(
                        title='URL to download output results',
                        type=openapi.TYPE_STRING
                    ),
                },
                example={
                    'request_id': 'af9c24a0-02cf-4a12-beb2-fac126a9c709',
                    'status': 'DONE',
                    'error': None,
                    'output_url': (
                        '{base_url}/api/v1/search/view/'
                        'cd20c26b-ac26-47c3-8b73-a998cb1efff7/'
                        'entity/batch/identifier/result/'
                        'af9c24a0-02cf-4a12-beb2-fac126a9c709/'
                    )
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityBatchSearchIdStatus, self).get(
            request, *args, **kwargs
        )


class ViewEntityBatchSearchIdResult(
    EntityBatchSearchIdResult, DatasetViewDetailCheckPermission
):
    """
    Fetch output results of batch search by id

    Return the json of batch search by id.
    Possible output:

    - If return_type is specified, then the results would be:
    ```
        'results': {
            'PAK': ['TST1_PAK_V1', 'TST1_PAK_V2'],
            'MWI': ['TST1_MWI_V2']
        }
    ```

    - If return_type is not specified, then the results will have
    full entity detail with following fields:

        | Field | Description |
        |---|---|
        | name | Geographical entity name |
        | ucode | Unicef code |
        | concept_ucode | Concept Unicef code |
        | uuid | UUID revision |
        | concept_uuid | UUID that persist between revision |
        | admin_level | Admin level of geographical entity |
        | level_name | Admin level name |
        | type | Name of entity type |
        | start_date | Start date of this geographical entity revision |
        | end_date | End date of this geographical entity revision |
        | ext_codes | Other external codes |
        | names | Other names with ISO2 language code |
        | is_latest | True if this is latest revision |
        | parents | All parents in upper level |
        | bbox | Bounding box of this geographical entity |
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET_VIEW

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='batch-result-search-view-by-id',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='View UUID', type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'request_id', openapi.IN_PATH,
                description=(
                    'Task Request ID'
                ),
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Schema(
                title='Geojson file',
                description=(
                    'Geojson that contains geocoding output in '
                    'the properties.'
                ),
                type=openapi.TYPE_FILE,
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityBatchSearchIdResult, self).get(
            request, *args, **kwargs
        )


class ViewEntityBatchGeocodingStatus(
    EntityBatchGeocodingStatus, DatasetViewDetailCheckPermission
):
    """
    Check status of batch geocoding

    Task is completed when status is one of DONE, ERROR, or CANCELLED.
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = GeocodingRequestType.DATASET_VIEW
    result_url = 'v1:get-result-batch-geocoding'

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='check-status-batch-geocoding',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='View UUID', type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'request_id', openapi.IN_PATH,
                description=(
                    'Task Request ID'
                ),
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Schema(
                title='Geocoding Batch Task Status',
                type=openapi.TYPE_OBJECT,
                properties={
                    'request_id': openapi.Schema(
                        title='Request ID',
                        type=openapi.TYPE_STRING
                    ),
                    'status': openapi.Schema(
                        title=(
                            'Task Status. One of PENDING, PROCESSING, DONE, '
                            'ERROR, CANCELLED'
                        ),
                        type=openapi.TYPE_STRING
                    ),
                    'error': openapi.Schema(
                        title=(
                            'Error when batch job is failed'
                        ),
                        type=openapi.TYPE_STRING
                    ),
                    'output_url': openapi.Schema(
                        title='URL to download output GeoJSON File',
                        type=openapi.TYPE_STRING
                    ),
                },
                example={
                    'request_id': 'af9c24a0-02cf-4a12-beb2-fac126a9c709',
                    'status': 'DONE',
                    'error': None,
                    'output_url': (
                        '{base_url}/api/v1/search/view/'
                        'cd20c26b-ac26-47c3-8b73-a998cb1efff7/'
                        'batch-containment-check/result/'
                        'af9c24a0-02cf-4a12-beb2-fac126a9c709/'
                    )
                }
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityBatchGeocodingStatus, self).get(
            request, *args, **kwargs
        )


class ViewEntityBatchGeocodingResult(
    EntityBatchGeocodingResult, DatasetViewDetailCheckPermission
):
    """
    Fetch geojson output of batch geocoding

    Return the geojson that contains geocoding output in one of the properties.
    """
    permission_classes = [DatasetViewDetailAccessPermission]
    request_type = GeocodingRequestType.DATASET_VIEW

    def get_request_object(self, request, kwargs):
        view, _ = self.get_dataset_view_obj(request, kwargs.get('uuid', None))
        return view.id, view.uuid

    @swagger_auto_schema(
        operation_id='get-result-batch-geocoding',
        tags=[OPERATION_VIEW_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='View UUID', type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'request_id', openapi.IN_PATH,
                description=(
                    'Task Request ID'
                ),
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: openapi.Schema(
                title='Geojson file',
                description=(
                    'Geojson that contains geocoding output in '
                    'the properties.'
                ),
                type=openapi.TYPE_FILE,
            ),
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewEntityBatchGeocodingResult, self).get(
            request, *args, **kwargs
        )


class ViewFindEntityByUCode(
    FindEntityByUCode, DatasetViewDetailCheckPermission
):
    """
    Find entity by ucode within a view.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    def find_parent_resource(self, entity_qs, request, kwargs):
        """Find dataset from the entity queryset or request object."""
        dataset_view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        dataset = dataset_view.dataset

        return dataset, dataset_view, max_privacy_level

    @swagger_auto_schema(
        operation_id='search-view-entity-by-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'ucode', openapi.IN_PATH,
            description='Entity UCode',
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: FindEntityByUCodeSerializer,
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewFindEntityByUCode, self).get(
            request, *args, **kwargs
        )


class ViewFindEntityByCUCode(
    FindEntityByCUCode, DatasetViewDetailCheckPermission
):
    """
    Find entity by concept ucode within a view.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [DatasetViewDetailAccessPermission]

    def find_parent_resource(self, entity_qs, request, kwargs):
        """Find dataset from the entity queryset or request object."""
        dataset_view, max_privacy_level = self.get_dataset_view_obj(
            request, kwargs.get('uuid', None)
        )
        dataset = dataset_view.dataset

        return dataset, dataset_view, max_privacy_level

    @swagger_auto_schema(
        operation_id='search-view-entity-by-concept-ucode',
        tags=[SEARCH_VIEW_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='View UUID', type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'concept_ucode', openapi.IN_PATH,
            description='Entity Concept UCode',
            type=openapi.TYPE_STRING
        ), openapi.Parameter(
            'geom', openapi.IN_QUERY,
            description=(
                'Geometry format: '
                '[no_geom, centroid, full_geom]'
            ),
            type=openapi.TYPE_STRING,
            default='no_geom',
            required=False
        ), openapi.Parameter(
            'format', openapi.IN_QUERY,
            description='Output format: [json, geojson]',
            type=openapi.TYPE_STRING,
            default='json',
            required=False
        )],
        responses={
            200: openapi.Schema(
                title='Entity List',
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties=(
                        FindEntityByUCodeSerializer.Meta.
                        swagger_schema_fields['properties']
                    )
                ),
                example=[
                    (
                        FindEntityByUCodeSerializer.Meta.
                        swagger_schema_fields['example']
                    )
                ]
            ),
            400: APIErrorSerializer,
            404: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        return super(ViewFindEntityByCUCode, self).get(
            request, *args, **kwargs
        )
