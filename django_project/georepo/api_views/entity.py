import os
import json
import math
from typing import Tuple
from datetime import datetime
from dateutil.parser import isoparse
from django.db import connection
from django.db.models.expressions import RawSQL
from django.http import Http404, FileResponse
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models import Extent
from core.models.preferences import SitePreferences
from django.db.models import (
    FilteredRelation, Q, Value, F, IntegerField
)
from django.db.models.functions import Replace, Greatest
from django.contrib.postgres.search import TrigramWordSimilarity
from django.core.paginator import Paginator
from rest_framework.renderers import JSONRenderer
from georepo.utils.renderers import GeojsonRenderer
from georepo.utils.permission import (
    DatasetDetailAccessPermission,
    get_view_permission_privacy_level,
    get_external_view_permission_privacy_level
)

from core.mixins import APILoggingMixin
from georepo.api_views.api_cache import ApiCache
from georepo.models import (
    Dataset,
    GeographicalEntity,
    IdType,
    EntityId,
    EntityType,
    DatasetView
)
from georepo.serializers.entity import (
    SearchEntitySerializer,
    SearchGeometrySerializer,
    GeographicalEntitySerializer,
    GeographicalGeojsonSerializer,
    FindEntityByUCodeSerializer,
    FindEntityByUcodeGeojsonSerializer
)
from georepo.models.base_task_request import PENDING, COMPLETED_STATUS, DONE
from georepo.models.search_id_request import (
    SearchIdRequest,
    SearchIdRequestType
)
from georepo.serializers.common import APIErrorSerializer
from georepo.utils.geojson import validate_geojson
from georepo.models.entity import (
    MAIN_ENTITY_ID_LIST,
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID
)
from georepo.utils.unique_code import (
    parse_unique_code,
    get_unique_code,
    try_parse_unique_code
)
from georepo.utils.url_helper import get_ucode_from_url_path
from georepo.utils.uuid_helper import get_uuid_value
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_ENTITY_TAG,
    OPERATION_ENTITY_TAG,
    CONTROLLED_LIST_TAG,
    SEARCH_DATASET_ENTITY_TAG,
    SEARCH_ENTITY_BASE_TAG
)
from georepo.utils.api_parameters import (
    common_api_params,
    sort_param,
    APISortBase,
    search_param,
    search_type_param
)
from georepo.utils.entity_query import (
    GeomReturnType,
    do_generate_entity_query,
    validate_return_type
)
from georepo.tasks.search_id import (
    process_search_id_request
)
from georepo.models.geocoding_request import (
    GeocodingRequestType,
    GeocodingRequest,
    GEOJSON,
    SHAPEFILE,
    GEOPACKAGE
)
from georepo.tasks.geocoding import process_geocoding_request
from georepo.utils.shapefile import (
    validate_shapefile_zip
)
from georepo.utils.layers import (
    validate_layer_file_metadata
)
from georepo.utils.dataset_view import check_entity_in_view


class DatasetDetailCheckPermission(object):

    def get_dataset_obj(self, request, kwargs, search_source='Dataset'):
        """
        Check dataset obj permission and return max_privacy_level for read
        """
        uuid = kwargs.get('uuid')
        dataset = get_object_or_404(
            Dataset,
            uuid=uuid,
            module__is_active=True
        )
        dataset_view = None
        if search_source == 'Dataset':
            self.check_object_permissions(request, dataset)
        elif search_source == 'View':
            # for View, no need to call check_object_permissions again
            dataset_view = DatasetView.objects.filter(
                uuid=kwargs.get('view_uuid', None)).first()
        # retrieve user privacy level for this dataset
        max_privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset,
            dataset_view=dataset_view
        )
        if max_privacy_level == 0:
            raise PermissionDenied(
                'You are not allowed to '
                f'access this {search_source.lower()}'
            )
        return dataset, max_privacy_level


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='id-type-list',
                tags=[CONTROLLED_LIST_TAG],
                responses={
                    200: openapi.Schema(
                        title='ID Type List',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_STRING
                        ),
                        example=[
                            'PCode',
                            'GID'
                        ]
                    )
                }
            )
)
class EntityIdList(APILoggingMixin, APIView):
    """
    Get entity id types

    Return available entity id types in system
    Example entity id types: uuid, ucode, PCode
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        id_types = IdType.objects.values_list('name', flat=True)
        result = list(id_types)
        for main_id in MAIN_ENTITY_ID_LIST:
            if main_id not in result:
                result.append(main_id)
        return Response(status=200, data=result)


class EntityBoundingBox(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Find bounding box of geographical entity

    Search Geographical Entity by id_type and its identifier value \
    and return its bounding box

    Example usage:
    id_type=PCode, id=PAK
    ```
    GET /operation/dataset/{uuid}/bbox/PCode/PAK/
    ```
    """
    permission_classes = [DatasetDetailAccessPermission]
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID',
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
        operation_id='operation-bbox',
        tags=[OPERATION_ENTITY_TAG],
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
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs
        )
        req_label = kwargs.get('id_type', '').lower()
        req_id = kwargs.get('id', '')
        bbox = None
        if req_label in MAIN_ENTITY_ID_LIST:
            entities = GeographicalEntity.objects.filter(
                is_approved=True,
                dataset=dataset,
                privacy_level__lte=max_privacy_level
            )
            if req_label == UUID_ENTITY_ID:
                uuid_val = get_uuid_value(req_id)
                entities = entities.filter(
                    uuid_revision=uuid_val
                )
            elif req_label == CONCEPT_UUID_ENTITY_ID:
                uuid_val = get_uuid_value(req_id)
                entities = entities.filter(
                    uuid=uuid_val
                )
            elif req_label == CODE_ENTITY_ID:
                entities = entities.filter(
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
                entities = entities.filter(
                    unique_code=ucode,
                    unique_code_version=version
                )
            elif req_label == CONCEPT_UCODE_ENTITY_ID:
                entities = entities.filter(
                    concept_ucode=req_id
                )
            if entities.exists():
                bbox = entities.aggregate(
                    Extent('geometry')
                )['geometry__extent']
        else:
            entity_id = EntityId.objects.filter(
                code__name__iexact=req_label,
                value=req_id,
                geographical_entity__is_approved=True,
                geographical_entity__dataset=dataset,
                geographical_entity__privacy_level__lte=max_privacy_level
            ).select_related(
                'geographical_entity'
            ).order_by('geographical_entity__id')
            if entity_id.exists():
                bbox = entity_id.aggregate(
                    Extent('geographical_entity__geometry')
                )['geographical_entity__geometry__extent']
        if not bbox:
            raise Http404('No GeographicalEntity matches the given query.')
        return Response(bbox)


class EntityListBoundingBox(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Find bounding box of geographical entities

    Search Geographical Entity by id_type and its identifier values \
    and return its bounding box. id_type can be ucode or concept_uuid.

    Example usage:
    id_type=ucode
    ```
    POST /operation/dataset/{uuid}/bbox/ucode/

    Request body:
        ["PAK_V1", "IND_V1"]
    ```
    """
    permission_classes = [DatasetDetailAccessPermission]
    # [Dataset, View]
    search_source = 'Dataset'
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID',
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
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs
        )

        entities = GeographicalEntity.objects.filter(
            is_approved=True,
            dataset=dataset,
            privacy_level__lte=max_privacy_level
        )
        return entities

    @swagger_auto_schema(
        operation_id='operation-bbox-post',
        tags=[OPERATION_ENTITY_TAG],
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
        req_label = kwargs.get('id_type', '').lower()
        if req_label not in [UCODE_ENTITY_ID, CONCEPT_UUID_ENTITY_ID]:
            return Response(
                status=400,
                data={
                    'detail': (
                        'Invalid id_type. Only ucode and concept_uuid '
                        'are allowed.'
                    )
                }
            )
        id_values = request.data

        entities = self._get_entities_query(request, kwargs)
        if req_label == CONCEPT_UUID_ENTITY_ID:
            uuid_vals = [get_uuid_value(id_value) for id_value in id_values]
            entities = entities.filter(
                uuid__in=uuid_vals
            )
        elif req_label == UCODE_ENTITY_ID:
            q = Q()
            for id_value in id_values:
                try:
                    ucode, version = parse_unique_code(id_value.upper())
                    q |= Q(
                        unique_code__iexact=ucode,
                        unique_code_version=version
                    )
                except ValueError:
                    pass
            entities = entities.filter(q)

        bbox = None
        if entities.exists():
            bbox = entities.aggregate(
                Extent('geometry')
            )['geometry__extent']

        if not bbox:
            raise Http404('No GeographicalEntity matches the given query.')
        return Response(
            bbox
        )


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='entity-type-list',
                tags=[CONTROLLED_LIST_TAG],
                responses={
                    200: openapi.Schema(
                        title='Entity Types',
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Items(
                            type=openapi.TYPE_STRING
                        ),
                        example=[
                            'Country',
                            'Province'
                        ]
                    )
                }
            )
)
class EntityTypeList(APILoggingMixin, APIView):
    """
    Get admin level types

    Return admin level types:
    Example entity type list: ['Country', 'District']
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        types = EntityType.objects.annotate(
            sanitized_label=Replace(
                'label',
                Value(' '),
                Value('_')
            )
        ).values_list(
            'sanitized_label',
            flat=True
        )
        return Response(status=200, data=types)


class EntityContainmentCheck(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Find geographical entity using spatial query

    Given Geojson data in the payload, find the identifier value \
        of {id_type} from Geographical Entity in the dataset\
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
    POST /operation/dataset/{uuid}/containment-check/
        ST_Intersects/0/ucode/?admin_level=0
    Request Content-type: application/json
    Request Body: Geojson
    ```
    """
    permission_classes = [DatasetDetailAccessPermission]
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID',
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

    def validate_level_type(self, level_type: str) -> bool:
        if not level_type:
            return True, None
        entity_types = EntityType.objects.annotate(
                            sanitized_label=Replace(
                                'label',
                                Value(' '),
                                Value('_')
                            )
                        ).filter(
                            sanitized_label=level_type
                        )
        return entity_types.exists(), entity_types.first()

    def validate_query_type(self, query_type: str) -> bool:
        query_list = [
                'ST_Intersects',
                'ST_Within',
                'ST_Within(ST_Centroid)',
                'ST_DWithin'
        ]
        return query_type in query_list

    def validate_return_type(self, return_type: str) -> IdType | str:
        if not return_type:
            return False
        id_type = IdType.objects.filter(
            name__iexact=return_type
        )
        if id_type.exists():
            return id_type.first()
        # check whether id_type is uuid, Code
        if return_type in MAIN_ENTITY_ID_LIST:
            return return_type
        return None

    def get_id_value(self, id_type, results, is_hierarchical,
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
                    str(id_key): self.entities_code(geo_id, id_type,
                                                    max_privacy_level)
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
            spatial_query: str,
            dwithin_distance: int,
            geom: GEOSGeometry,
            max_privacy_level: int,
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
        query = (
            query +
            'gg.is_approved=true AND gg.is_latest=true AND '
            'gg.privacy_level<=%s AND '
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

    def entities_code(self, parent_entity_id, id_type, max_privacy_level):
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
            if (
                GeographicalEntity.objects.filter(
                    parent__id=entity_id,
                    is_approved=True,
                    is_latest=True,
                    privacy_level__lte=max_privacy_level
                ).exists()
            ):
                codes.append({
                    str(key): self.entities_code(entity_id, id_type,
                                                 max_privacy_level)
                })
            else:
                codes.append(str(key))
        return codes

    @swagger_auto_schema(
        operation_id='operation-containment-check',
        tags=[OPERATION_ENTITY_TAG],
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
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs
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
        level_type = request.query_params.get('entity_type', None)
        valid_level_type, entity_type = self.validate_level_type(level_type)
        if not valid_level_type:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Invalid Entity Type: {level_type}.'
                }).data
            )
        admin_level = request.query_params.get('admin_level', None)
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
                        dataset,
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
                    self.get_id_value(id_type, results, is_hierarchical,
                                      max_privacy_level)
                )
        elif geojson['type'] == 'FeatureCollection':
            for idx, feature in enumerate(geojson['features']):
                results = self.do_run_query(
                            return_type,
                            id_type,
                            dataset,
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
                        self.get_id_value(id_type, results, is_hierarchical,
                                          max_privacy_level)
                    )
        return Response(
            geojson
        )


class EntitySearchBase(ApiCache, DatasetDetailCheckPermission, APISortBase):
    cache_model = Dataset
    renderer_classes = [JSONRenderer, GeojsonRenderer]
    # [Dataset, View]
    search_source = 'Dataset'
    permission_classes = [DatasetDetailAccessPermission]
    # some of APIs will not have search_text parameters
    enable_search_text = True

    def get_trigram_similarity(self):
        # fetch from site preferences
        return SitePreferences.preferences().search_similarity

    def get_search_fuzzy_config(self):
        return SitePreferences.preferences().api_config.get(
            'use_fuzzy_search',
            True
        )

    def sanitize_search_text(self, search_text):
        """
        sanitize the search text
        """
        # strip null characters
        search_text = search_text.replace('\x00', '')
        return search_text

    def _fuzzy_search_entity_names(self, entities, names, search_text):
        """Search using fuzzy search of entity names.

        Note: this method is not optimised because
            it does not uses trigram index.
            Check the implementation of fuzzy search in view.
        """
        similarities = []
        if names['idx__max'] is not None:
            for name_idx in range(names['idx__max'] + 1):
                field_key = f"name_{name_idx}__name"
                similarities.append(
                    TrigramWordSimilarity(
                        F(field_key),
                        Value(search_text)
                    )
                )
        if len(similarities) == 1:
            annotation = {
                'similarity': similarities[0]
            }
        elif len(similarities) > 1:
            annotation = {
                'similarity': Greatest(
                    *similarities
                )
            }
        else:
            annotation = {
                'similarity': Value(0, output_field=IntegerField())
            }
        entities = entities.annotate(**annotation).filter(
            similarity__gte=self.get_trigram_similarity()
        ).order_by('-similarity')
        return entities

    def _search_entity_names(self, entities, names, search_text):
        """Search using icontains of entity names."""
        if names['idx__max'] is not None:
            query = Q()
            for name_idx in range(names['idx__max'] + 1):
                field_key = f"name_{name_idx}__name__icontains"
                query |= Q(**{field_key: search_text})
            entities = entities.filter(query)

        return entities

    def search_query_by_entity_name(
        self, entities, names, search_text, is_fuzzy=True
    ):
        """Search query by entity name."""
        if is_fuzzy:
            return self._fuzzy_search_entity_names(
                entities, names, search_text
            )

        return self._search_entity_names(
            entities, names, search_text
        )

    def search_query_by_ucode(self, entities, search_text):
        """Search query by ucode text."""
        unique_code, version = try_parse_unique_code(search_text)
        entities = entities.filter(
            unique_code__icontains=unique_code
        )
        if version:
            entities = entities.filter(
                unique_code_version=version
            )
        return entities

    def get_serializer(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        return (
            GeographicalGeojsonSerializer if format == 'geojson'
            else GeographicalEntitySerializer
        )

    def generate_entity_query(
        self,
        entities,
        dataset_id,
        entity_type=None,
        admin_level=None
    ):
        # centroid, full_geom, no_geom. Default to no_geom
        geom_type = self.request.GET.get('geom', 'no_geom')
        geom_type = GeomReturnType.from_str(geom_type)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        entities, values, max_level, ids, names_max_idx = (
            do_generate_entity_query(
                entities, dataset_id, entity_type,
                admin_level, geom_type, format)
        )
        return entities.values(*values), max_level, ids, names_max_idx

    def generate_response(self, entities, context=None) -> Tuple[dict, dict]:
        """
        Return (paginated response, response headers)
        """
        # pagination parameter
        page = int(self.request.GET.get('page', '1'))
        page_size = get_page_size(self.request)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        output = []
        total_page = 0
        total_count = 0
        if entities is not None:
            # set pagination
            paginator = Paginator(entities, page_size)
            total_page = math.ceil(paginator.count / page_size)
            total_count = paginator.count
            if page > total_page:
                output = []
                output = (
                    self.get_serializer()(
                        output,
                        many=True,
                        context=context
                    ).data
                )
            else:
                paginated_entities = paginator.get_page(page)
                output = (
                    self.get_serializer()(
                        paginated_entities,
                        many=True,
                        context=context
                    ).data
                )
        else:
            output = (
                self.get_serializer()(
                    output,
                    many=True,
                    context=context
                ).data
            )
        if format == 'geojson':
            return output, {
                'page': page,
                'total_page': total_page,
                'page_size': page_size,
                'count': total_count
            }
        return {
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'count': total_count,
            'results': output
        }, None

    def get_response_data(self, request, *args, **kwargs):
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )
        # entity type
        entity_type = kwargs.get('entity_type', None)
        # admin level
        admin_level = kwargs.get('admin_level', None)
        # ancestor ucode
        ancestor_ucode = kwargs.get('ucode', None)
        # concept ucode filter
        ancestor_concept_ucode = kwargs.get('concept_ucode', None)
        # search
        search_text = request.GET.get('search', '')
        search_text = self.sanitize_search_text(search_text)
        search_type = request.GET.get('search_type', 'name')

        # find entity type:
        if entity_type:
            entity_type = EntityType.objects.annotate(
                sanitized_label=Replace(
                    'label',
                    Value(' '),
                    Value('_')
                )
            ).filter(
                sanitized_label__iexact=entity_type.lower()
            ).first()

        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True
        )
        # filter the entities with max privacy level from user permision
        entities = entities.filter(
            privacy_level__lte=max_privacy_level
        )
        if self.search_source == 'Dataset':
            is_latest = request.GET.get('is_latest', 'true')
            if is_latest.lower() == 'true':
                entities = entities.filter(
                    is_latest=True
                )

        if entity_type:
            entities = entities.filter(
                type=entity_type.id
            )
        if admin_level is not None:
            entities = entities.filter(
                level=admin_level
            )
        if ancestor_ucode:
            try:
                ancestor_ucode, version = parse_unique_code(ancestor_ucode)
            except ValueError:
                return self.generate_response(None)
            entities = entities.filter(
                (
                    Q(ancestor__unique_code=ancestor_ucode) &
                    Q(ancestor__unique_code_version=version)
                ) | (
                    Q(ancestor__isnull=True) &
                    Q(unique_code=ancestor_ucode) &
                    Q(unique_code_version=version)
                )
            )
        if ancestor_concept_ucode:
            entities = entities.filter(
                (
                    Q(ancestor__concept_ucode=ancestor_concept_ucode)
                ) | (
                    Q(ancestor__isnull=True) &
                    Q(concept_ucode=ancestor_concept_ucode)
                )
            )

        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id,
            entity_type=entity_type,
            admin_level=admin_level
        )

        if self.enable_search_text and search_text:
            if search_type == 'name':
                # use icontains, not the fuzzy search
                entities = self.search_query_by_entity_name(
                    entities,
                    names,
                    search_text,
                    False
                )
            elif search_type == 'ucode':
                entities = self.search_query_by_ucode(
                    entities, search_text
                )

        # sort
        entities = self.sort_queryset(request, entities)

        return self.generate_response(
            entities,
            context={
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )


class EntityFuzzySearch(EntitySearchBase):
    """
    Find geographical entity by name

    Fuzzy search geographical entity by {search_text}
    If {is_latest} is provided, the API will only search \
    for entity with filter {is_latest} (default is True)

    Example request:
    ```
    GET /search/dataset/{uuid}/entity/PAK/?is_latest=True
    ```
    """
    enable_search_text = False
    dataset_uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID', type=openapi.TYPE_STRING
    )
    search_param = openapi.Parameter(
        'search_text', openapi.IN_PATH,
        description='search text',
        type=openapi.TYPE_STRING
    )
    is_latest_param = openapi.Parameter(
        'is_latest', openapi.IN_QUERY,
        description='True to search for latest entity only',
        type=openapi.TYPE_BOOLEAN,
        default=True,
        required=False
    )
    geom_param = openapi.Parameter(
        'geom', openapi.IN_QUERY,
        description='[no_geom, centroid, full_geom]',
        type=openapi.TYPE_STRING,
        default='no_geom',
        required=False
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='[json, geojson]',
        type=openapi.TYPE_STRING,
        default='json',
        required=False
    )

    def get_serializer(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        return (
            GeographicalGeojsonSerializer if format == 'geojson'
            else SearchEntitySerializer
        )

    def generate_response(self, entities, context=None):
        # pagination parameter
        page = int(self.request.GET.get('page', '1'))
        page_size = get_page_size(self.request)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        output = []
        total_page = 0
        total_count = 0
        if entities is not None:
            # set pagination
            paginator = Paginator(entities, page_size)
            total_page = math.ceil(paginator.count / page_size)
            total_count = paginator.count
            if page > total_page:
                output = []
            else:
                paginated_entities = paginator.get_page(page)
                output = (
                    self.get_serializer()(
                        paginated_entities,
                        many=True,
                        context=context
                    ).data
                )
        if format == 'geojson':
            return Response(
                output,
                headers={
                    'page': page,
                    'total_page': total_page,
                    'page_size': page_size,
                    'count': total_count,
                }
            )
        return Response(data={
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'count': total_count,
            'results': output
        })

    @swagger_auto_schema(
        operation_id='search-entity-by-name',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[
            dataset_uuid_param, search_param, is_latest_param,
            *common_api_params,
            geom_param, format_param
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
                            'count': openapi.Schema(
                                title='Total Count',
                                type=openapi.TYPE_INTEGER
                            ),
                            'page_size': openapi.Schema(
                                title='Total item in 1 page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'results': openapi.Schema(
                                title='List of geographical entity',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties=(
                                        SearchEntitySerializer.Meta.
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
                                    SearchEntitySerializer.Meta.
                                    swagger_schema_fields['example']
                                )
                            ]
                        }
                    ),
            400: APIErrorSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        search_text = kwargs.get('search_text', '')
        search_text = self.sanitize_search_text(search_text)
        if not search_text:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'search_text is mandatory!'
                }).data
            )
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )
        entities = GeographicalEntity.objects.filter(
            is_approved=True,
            dataset=dataset,
            privacy_level__lte=max_privacy_level
        )
        is_latest = request.GET.get('is_latest', None)
        if is_latest is not None:
            is_latest = is_latest.lower() == 'true'
            entities = entities.filter(
                is_latest=is_latest
            )
        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id
        )
        entities = self.search_query_by_entity_name(
            entities, names, search_text, is_fuzzy=True
        )
        return self.generate_response(
            entities,
            context={
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )


class EntityGeometryFuzzySearch(EntitySearchBase):
    """
    Find closest geographical entities

    Search top 10 Geographical Entity that has closest match with \
        given geometry
    If {is_latest} is provided, the API will only search \
    for entity with {is_latest} (default is True)

    Example request:
    ```
    POST /search/dataset/{uuid}/entity/geometry/?is_latest=True
    Request Content-type: application/json
    Request Body: Geojson
    ```
    """
    enable_search_text = False
    dataset_uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID', type=openapi.TYPE_STRING
    )
    level_param = openapi.Parameter(
        'admin_level', openapi.IN_QUERY,
        description='Admin level. Example: 0',
        type=openapi.TYPE_INTEGER,
        required=False
    )
    is_latest_param = openapi.Parameter(
        'is_latest', openapi.IN_QUERY,
        description='True to search for latest entity only',
        type=openapi.TYPE_BOOLEAN,
        default=True,
        required=False
    )
    geom_param = openapi.Parameter(
        'geom', openapi.IN_QUERY,
        description=(
            'Geometry format: '
            '[no_geom, centroid, full_geom]'
        ),
        type=openapi.TYPE_STRING,
        default='no_geom',
        required=False
    )
    format_param = openapi.Parameter(
        'format', openapi.IN_QUERY,
        description='Output format: [json, geojson]',
        type=openapi.TYPE_STRING,
        default='json',
        required=False
    )
    geojson_body = openapi.Schema(
        description='Geometry data (SRID 4326) in geojson format',
        type=openapi.TYPE_STRING
    )

    def get_simplify_tolerance(self):
        # fetch from site preferences
        return SitePreferences.preferences().search_simplify_tolerance

    def generate_query(
            self,
            geom,
            is_latest,
            levels,
            dataset_uuid,
            max_privacy_level):
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
            'FROM georepo_geographicalentity gg '
            'left join georepo_geographicalentity parent_0 on ( '
            '    parent_0.id = gg.ancestor_id '
            ') '
            'WHERE gg.is_approved AND ST_Intersects(gg.geometry, %s) AND '
            'gg.privacy_level<=%s'
        )
        conditions = []
        if is_latest is not None:
            conditions.append('gg.is_latest=%s')
            query_values.append(is_latest)
        if levels:
            conditions.append('gg.level IN %s')
            query_values.append(tuple(levels))
        if dataset_uuid:
            conditions.append('gg.dataset_id IN %s')
            query_values.append(tuple(
                Dataset.objects.filter(
                    uuid=dataset_uuid
                ).values_list('id', flat=True)
            ))
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

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, *args, **kwargs):
        pass

    @swagger_auto_schema(
        operation_id='search-entity-by-geometry',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[
            dataset_uuid_param, level_param,
            is_latest_param, geom_param, format_param
        ],
        request_body=geojson_body,
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
            400: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )
        level = request.GET.get('admin_level', None)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        is_latest = request.GET.get('is_latest', None)
        if is_latest is not None:
            is_latest = is_latest.lower() == 'true'
        geojson = request.data
        if not validate_geojson(geojson):
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid Geojson Data.'
                }).data
            )
        if geojson['type'] == 'FeatureCollection':
            feature = geojson['features'][0]
        else:
            feature = geojson
        geom = GEOSGeometry(
                json.dumps(feature['geometry']), srid=4326
        )
        levels = []
        if level is not None:
            levels.append(level)
        sql, query_values = self.generate_query(
            geom, is_latest, levels, str(dataset.uuid), max_privacy_level)
        entities_raw = GeographicalEntity.objects.raw(sql, query_values)
        entities = GeographicalEntity.objects.filter(
            id__in=[getattr(entity, 'id', None) for entity in entities_raw]
        )
        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id
        )
        if format == 'geojson':
            output = GeographicalGeojsonSerializer(
                entities,
                many=True,
                context={
                    'max_level': max_level,
                    'ids': ids,
                    'names': names
                }
            ).data
        else:
            output = sorted(
                    SearchGeometrySerializer(
                        entities,
                        many=True,
                        context={
                            'max_level': max_level,
                            'ids': ids,
                            'names': names,
                            'entities_raw': entities_raw
                        }).data,
                    key=lambda x: x['distance']
            )
        return Response(
            status=200,
            data={
                'page': 1,
                'total_page': 1,
                'page_size': 10,
                'count': entities.count(),
                'results': output
            }
        )


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-entity-by-type',
                tags=[SEARCH_ENTITY_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
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
)
class EntityList(EntitySearchBase):
    """
    Find list of geographical entity by entity type in dataset

    Retrieve list of geographical entity in dataset \
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


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-entity-by-type-and-ucode',
                tags=[SEARCH_ENTITY_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
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
)
class EntityListByUCode(EntitySearchBase):
    """
    Find list of geographical entity by entity type and parent ucode in dataset

    Retrieve list of geographical entity in dataset \
    with filter type={entity_type} and parent ucode={ucode}
    For available entity_type in dataset, can refer to \
    API search-dataset-detail

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


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-entity-by-level',
                tags=[SEARCH_ENTITY_TAG, SEARCH_DATASET_ENTITY_TAG],
                manual_parameters=[
                    openapi.Parameter(
                        'uuid', openapi.IN_PATH,
                        description='Dataset UUID', type=openapi.TYPE_STRING
                    ),
                    openapi.Parameter(
                        'admin_level', openapi.IN_PATH,
                        description=(
                            'Admin level of the entity'
                        ),
                        type=openapi.TYPE_INTEGER
                    ),
                    *common_api_params, sort_param,
                    search_param, search_type_param,
                    openapi.Parameter(
                        'geom', openapi.IN_QUERY,
                        description=(
                            'Geometry format: '
                            '[no_geom, centroid, full_geom]'
                        ),
                        type=openapi.TYPE_STRING,
                        default='no_geom',
                        required=False
                    ),
                    openapi.Parameter(
                        'format', openapi.IN_QUERY,
                        description='Output format: [json, geojson]',
                        type=openapi.TYPE_STRING,
                        default='json',
                        required=False
                    ),
                    openapi.Parameter(
                        'is_latest', openapi.IN_QUERY,
                        description=(
                            'True to search for latest entity only. '
                            'Default to True.'
                        ),
                        type=openapi.TYPE_BOOLEAN,
                        default=True,
                        required=False
                    )
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
)
class EntityListByAdminLevel(EntitySearchBase):
    """
    Find list of geographical entity by level in dataset

    Retrieve list of geographical entity in dataset \
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
    sort_attribute_mapping = {
        'name': 'label',
        'ucode': 'unique_code',
        'start_date': 'start_date',
        'end_date': 'end_date',
        'is_latest': 'is_latest'
    }
    default_sort = []


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-entity-by-level-and-ucode',
                tags=[SEARCH_ENTITY_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
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
)
class EntityListByAdminLevelAndUCode(EntitySearchBase):
    """
    Find list of geographical entity by level and ancestor ucode in dataset

    Retrieve list of geographical entity in dataset \
    with filter level={admin_level} and ancestor ucode={ucode}

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


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-entity-by-id',
                tags=[SEARCH_ENTITY_TAG],
                manual_parameters=[openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
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
)
class FindEntityById(EntitySearchBase):
    """
    Find geographical entity in dataset by one of ID

    Return geographical entity detail that has identifier {id}\
    with type {id_type}
    For {id_type} list can be retrieved from API id-type-list

    Example request:
    ```
    GET /search/dataset/{dataset_uuid}/entity/identifier/PCode/PAK/
    GET /search/dataset/{dataset_uuid}/entity/identifier/ucode/PAK_001_V1/
    ```
    """
    enable_search_text = False

    def parse_timestamp(self, value):
        result = None
        try:
            result = isoparse(value)
        except ValueError:
            try:
                val = float(value)
                result = datetime.fromtimestamp(val)
            except Exception:
                pass
        return result

    def get_response_data(self, request, *args, **kwargs):
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )

        id_type = kwargs.get('id_type', None)
        id_type = id_type.lower() if id_type else None
        id_value = kwargs.get('id', None)

        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            privacy_level__lte=max_privacy_level
        )
        timestamp = request.GET.get('timestamp', None)
        if timestamp:
            timestamp = self.parse_timestamp(timestamp)
            if not timestamp:
                # invalid timestamp value
                return self.generate_response(None)
            entities = entities.filter(
                start_date__lte=timestamp
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timestamp)
            )
        if self.search_source == 'Dataset':
            entities = entities.filter(
                is_latest=True
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
                    return self.generate_response(None)
                entities = entities.filter(
                    unique_code=ucode,
                    unique_code_version=version
                )
            elif id_type == CONCEPT_UCODE_ENTITY_ID:
                entities = entities.filter(
                    concept_ucode=id_value
                )

        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id
        )
        if id_type not in MAIN_ENTITY_ID_LIST:
            searched_id = (
                [id for id in ids if id['code__name'].lower() == id_type]
            )
            if not searched_id:
                return self.generate_response(None)
            field_key = f"id_{searched_id[0]['code__id']}__value"
            filter_by_idtype = {
                field_key: id_value
            }
            entities = entities.filter(**filter_by_idtype)
        return self.generate_response(
            entities,
            context={
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )


class FindEntityVersionsByConceptUCode(EntitySearchBase):
    """
    Find all revision of geographical entities in dataset by Concept UCode

    Return geographical entity detail that has concept ucode {concept_ucode} \
        in dataset {uuid}.

    Example request:
    ```
    GET /search/dataset/{dataset_uuid}/entity/version/{concept_ucode}/
    GET /search/dataset/{dataset_uuid}/entity/version/
        {concept_ucode}/?timestamp=2014-12-05T12:30:45.123456-05:30
    ```
    """
    enable_search_text = False

    @swagger_auto_schema(
        operation_id='search-entity-versions-by-concept-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(FindEntityVersionsByConceptUCode, self).get(
            request, *args, **kwargs
        )

    def parse_timestamp(self, value):
        result = None
        try:
            result = isoparse(value)
        except ValueError:
            try:
                val = float(value)
                result = datetime.fromtimestamp(val)
            except Exception:
                pass
        return result

    def get_response_data(self, request, *args, **kwargs):
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )
        concept_ucode = kwargs.get('concept_ucode', None)
        ucode = kwargs.get('ucode', None)
        if concept_ucode is None and ucode is None:
            return self.generate_response(None)
        timestamp = request.GET.get('timestamp', None)
        if ucode:
            ucode, data = get_ucode_from_url_path(ucode, -1)
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            privacy_level__lte=max_privacy_level
        ).order_by('revision_number')
        if concept_ucode:
            entities = entities.filter(
                concept_ucode=concept_ucode
            )
        if ucode:
            try:
                ucode, version = parse_unique_code(ucode)
            except ValueError:
                return self.generate_response(None)
            entity = GeographicalEntity.objects.filter(
                unique_code=ucode,
                unique_code_version=version,
                dataset=dataset,
                is_approved=True,
                privacy_level__lte=max_privacy_level
            ).first()
            if entity:
                entities = entities.filter(
                    uuid=entity.uuid
                )
            else:
                return self.generate_response(None)
        if timestamp:
            timestamp = self.parse_timestamp(timestamp)
            if not timestamp:
                # invalid timestamp value
                return self.generate_response(None)
            entities = entities.filter(
                start_date__lte=timestamp
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timestamp)
            )
        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id
        )
        return self.generate_response(
            entities,
            context={
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )


class FindEntityVersionsByUCode(FindEntityVersionsByConceptUCode):
    """
    Find all revision of geographical entities in dataset by UCode

    Return geographical entity detail that has same concept uuid \
        with entity {ucode} in dataset {uuid}.

    Example request:
    ```
    GET /search/dataset/{dataset_uuid}/entity/version/{ucode}/
    GET /search/dataset/{dataset_uuid}/entity/version/
        {ucode}/?timestamp=2014-12-05T12:30:45.123456-05:30
    ```
    """

    @swagger_auto_schema(
        operation_id='search-entity-versions-by-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(FindEntityVersionsByUCode, self).get(
            request, *args, **kwargs
        )


class EntityListByAdminLevel0(EntityListByAdminLevel):
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

    @method_decorator(
        name='get',
        decorator=swagger_auto_schema(
            operation_id='search-entity-by-level-0',
            tags=[SEARCH_ENTITY_TAG, SEARCH_DATASET_ENTITY_TAG],
            manual_parameters=[
                openapi.Parameter(
                    'uuid', openapi.IN_PATH,
                    description='Dataset UUID', type=openapi.TYPE_STRING
                ),
                *common_api_params, sort_param,
                search_param, search_type_param,
                openapi.Parameter(
                    'geom', openapi.IN_QUERY,
                    description=(
                        'Geometry format: '
                        '[no_geom, centroid, full_geom]'
                    ),
                    type=openapi.TYPE_STRING,
                    default='no_geom',
                    required=False
                ),
                openapi.Parameter(
                    'format', openapi.IN_QUERY,
                    description='Output format: [json, geojson]',
                    type=openapi.TYPE_STRING,
                    default='json',
                    required=False
                ),
                openapi.Parameter(
                    'is_latest', openapi.IN_QUERY,
                    description=(
                        'True to search for latest entity only. '
                        'Default to True.'
                    ),
                    type=openapi.TYPE_BOOLEAN,
                    default=True,
                    required=False
                )
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
    )
    def get(self, request, *args, **kwargs):
        return super(EntityListByAdminLevel0, self).get(
            request, *args, **kwargs
        )

    def get_response_data(self, request, *args, **kwargs):
        kwargs['admin_level'] = 0
        return super(EntityListByAdminLevel0, self).get_response_data(
            request, *args, **kwargs
        )


class EntityTraverseHierarchyByUCode(EntitySearchBase):
    """
    Find parent from geographical entity with UCode

    Retrieve parent from Geographical Entity with {ucode} \
    in dataset

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
        child = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            unique_code=ucode,
            unique_code_version=version,
            privacy_level__lte=max_privacy_level
        )
        return child.values('parent__id', 'parent__level').first()

    def find_parent(self, kwargs, dataset, ucode, version, max_privacy_level):
        parent = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            unique_code=ucode,
            unique_code_version=version,
            privacy_level__lte=max_privacy_level
        ).first()
        return parent

    def get_response_data(self, request, *args, **kwargs):
        # get dataset by uuid
        dataset, max_privacy_level = self.get_dataset_obj(
            request, kwargs, self.search_source
        )
        # ucode
        ucode = kwargs.get('ucode', None)
        if ucode:
            try:
                ucode, version = parse_unique_code(ucode)
            except ValueError:
                return self.generate_response(None)
        else:
            return self.generate_response(None)
        admin_level = None
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
            privacy_level__lte=max_privacy_level
        )
        if self.traverse_direction == 'up':
            # find parent
            child = self.find_child(
                kwargs, dataset, ucode, version, max_privacy_level
            )
            if child:
                entities = entities.filter(
                    id=child['parent__id']
                )
                admin_level = child['parent__level']
            else:
                return self.generate_response(None)
        else:
            # find children
            parent = self.find_parent(
                kwargs, dataset, ucode, version, max_privacy_level
            )
            if parent:
                entities = entities.filter(
                    parent=parent
                )
                admin_level = parent.level + 1
            else:
                return self.generate_response(None)
        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            dataset.id,
            admin_level=admin_level
        )
        return self.generate_response(
            entities,
            context={
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )

    @swagger_auto_schema(
        operation_id='search-entity-parents-by-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(EntityTraverseHierarchyByUCode, self).get(
            request, *args, **kwargs
        )


class EntityTraverseChildrenHierarchyByUCode(
    EntityTraverseHierarchyByUCode
):
    """
    Find children from geographical entity with UCode

    Retrieve children from geographical entity with {ucode} \
    in dataset

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
        operation_id='search-entity-children-by-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(EntityTraverseChildrenHierarchyByUCode, self).get(
            request, *args, **kwargs
        )


class EntityListByAdminLevelAndConceptUCode(
    EntityListByAdminLevelAndUCode
):
    """
        Find entities by level and ancestor concept ucode in dataset

        Retrieve geographical entities in dataset \
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
        operation_id='search-entity-by-level-and-concept-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(EntityListByAdminLevelAndConceptUCode, self).get(
            request, *args, **kwargs
        )


class EntityBatchSearchId(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Batch search to find geographical entities in dataset by one of ID

    The search will be done in background and the result can be retrieved using
    API batch-result-search-dataset-by-id.
    For input_type and return_type can be retrieved from API id-type-list.
    If return_type is empty, then the output will be full entity detail.

    Example request:
    ```
    POST /search/dataset/{dataset_uuid}/batch/identifier/PCode/
    Request Body: [ "PAK", "MWI" ]
        ```
    """
    permission_classes = [DatasetDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET
    status_url = 'v1:batch-status-search-entity-by-id'

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    @swagger_auto_schema(
        operation_id='batch-search-entity-by-id',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='Dataset UUID', type=openapi.TYPE_STRING
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
                        '{base_url}/api/v1/search/entity/'
                        'cd20c26b-ac26-47c3-8b73-a998cb1efff7/batch/result/'
                        'af9c24a0-02cf-4a12-beb2-fac126a9c709/'
                    )
                }
            ),
            404: APIErrorSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        request_obj_id, request_obj_uuid = self.get_request_object(
            request, kwargs
        )
        input_type_str = kwargs.get('input_type')
        input_type = validate_return_type(input_type_str)
        if input_type is None:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Invalid Input Type {input_type_str}.'
                }).data
            )
        return_type_str = request.GET.get('return_type', None)
        if return_type_str:
            return_type = validate_return_type(return_type_str)
            if return_type is None:
                return Response(
                    status=400,
                    data=APIErrorSerializer({
                        'detail': f'Invalid Return Type {return_type_str}.'
                    }).data
                )
        id_value_list = request.data
        if id_value_list is None or len(id_value_list) == 0:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Invalid ID List in request body.'
                }).data
            )
        # first parameter: 0 for Dataset, 1 for View
        # second parameter: object id
        id_request = SearchIdRequest.objects.create(
            status=PENDING,
            submitted_on=timezone.now(),
            submitted_by=request.user,
            parameters=(
                f'({str(request_obj_id)},{self.request_type},)'
            ),
            input_id_type=input_type_str,
            output_id_type=return_type_str,
            input=id_value_list
        )
        task = process_search_id_request.delay(id_request.id)
        id_request.task_id = task.id
        id_request.save(update_fields=['task_id'])
        status_kwargs = {
            'uuid': str(request_obj_uuid),
            'request_id': str(id_request.uuid)
        }
        status_url = reverse(
            self.status_url, kwargs=status_kwargs, request=request
        )
        status_url = request.build_absolute_uri(status_url)
        if not settings.DEBUG:
            # if not dev env, then replace with https
            status_url = status_url.replace('http://', 'https://')
        return Response(
            status=200,
            data={
                'request_id': str(id_request.uuid),
                'status_url': status_url
            }
        )


class EntityBatchSearchIdStatus(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Check status of batch search by id

    Task is completed when status is one of DONE, ERROR, or CANCELLED.
    """
    permission_classes = [DatasetDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET
    result_url = 'v1:batch-result-search-entity-by-id'

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    @swagger_auto_schema(
        operation_id='batch-status-search-entity-by-id',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='Dataset UUID', type=openapi.TYPE_STRING
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
                        '{base_url}/api/v1/search/entity/'
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
        _, request_obj_uuid = self.get_request_object(
            request, kwargs
        )
        request_uuid = kwargs.get('request_id')
        id_request = get_object_or_404(SearchIdRequest, uuid=request_uuid)
        if id_request.status in COMPLETED_STATUS:
            output_url = None
            if id_request.status == DONE:
                output_kwargs = {
                    'uuid': str(request_obj_uuid),
                    'request_id': str(id_request.uuid)
                }
                output_url = reverse(
                    self.result_url, kwargs=output_kwargs, request=request
                )
                output_url = request.build_absolute_uri(output_url)
                if not settings.DEBUG:
                    # if not dev env, then replace with https
                    output_url = output_url.replace('http://', 'https://')
            return Response(
                status=200,
                data={
                    'request_id': str(id_request.uuid),
                    'status': id_request.status,
                    'error': id_request.errors,
                    'output_url': output_url
                }
            )
        return Response(
            status=200,
            data={
                'request_id': str(id_request.uuid),
                'status': id_request.status,
                'error': id_request.errors,
                'output_url': None
            }
        )


class EntityBatchSearchIdResult(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
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
    permission_classes = [DatasetDetailAccessPermission]
    request_type = SearchIdRequestType.DATASET

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    @swagger_auto_schema(
        operation_id='batch-result-search-entity-by-id',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='Dataset UUID', type=openapi.TYPE_STRING
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
        self.get_request_object(
            request, kwargs
        )
        request_uuid = kwargs.get('request_id')
        id_request = get_object_or_404(SearchIdRequest, uuid=request_uuid)
        if id_request.status == DONE and id_request.output_file:
            return FileResponse(
                id_request.output_file,
                as_attachment=True
            )
        return Response(
            status=404,
            data={
                'detail': 'Batch search id process is not completed yet.'
            }
        )


class EntityBatchGeocoding(EntityContainmentCheck):
    permission_classes = [DatasetDetailAccessPermission]
    parser_classes = (MultiPartParser,)
    uuid_param = openapi.Parameter(
        'uuid', openapi.IN_PATH,
        description='Dataset UUID',
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

    request_type = GeocodingRequestType.DATASET
    status_url = 'v1:entity-check-status-batch-geocoding'

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    def check_layer_type(self, filename: str) -> str:
        if (filename.lower().endswith('.geojson') or
                filename.lower().endswith('.json')):
            return GEOJSON
        elif filename.lower().endswith('.zip'):
            return SHAPEFILE
        elif filename.lower().endswith('.gpkg'):
            return GEOPACKAGE
        return ''

    def check_shapefile_zip(self, file_obj: any) -> str:
        _, error = validate_shapefile_zip(file_obj)
        if error:
            return ('Missing required file(s) inside zip file: \n- ' +
                    '\n- '.join(error)
                    )
        return ''

    def remove_temp_file(self, file_obj: any) -> None:
        if isinstance(file_obj, TemporaryUploadedFile):
            if os.path.exists(file_obj.temporary_file_path()):
                os.remove(file_obj.temporary_file_path())

    def validate_crs_type(self, file_obj: any, type: any):
        is_valid_crs, crs, _, _ = (
            validate_layer_file_metadata(file_obj, type)
        )
        return is_valid_crs, crs

    @swagger_auto_schema(
        operation_id='entity-batch-geocoding',
        tags=[OPERATION_ENTITY_TAG],
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
                        '{base_url}/api/v1/operation/dataset/'
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
        request_obj_id, request_obj_uuid = self.get_request_object(
            request, kwargs
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
        elif spatial_query != 'ST_DWithin':
            dwithin_distance = 0
        return_type_str = kwargs.get('id_type', None)
        return_type_str = return_type_str.lower() if return_type_str else None
        return_type = self.validate_return_type(return_type_str)
        if not return_type:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Invalid Type {return_type_str}.'
                }).data
            )
        admin_level = kwargs.get('admin_level', 0)
        file_obj = request.data['file']
        layer_type = self.check_layer_type(file_obj.name)
        if layer_type == '':
            self.remove_temp_file(file_obj)
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': 'Unrecognized file type!'
                }).data
            )
        if layer_type == SHAPEFILE:
            validate_shp_file = self.check_shapefile_zip(file_obj)
            if validate_shp_file != '':
                self.remove_temp_file(file_obj)
                return Response(
                    status=400,
                    data=APIErrorSerializer({
                        'detail': validate_shp_file
                    }).data
                )
        is_valid_crs, crs = self.validate_crs_type(file_obj, layer_type)
        if not is_valid_crs:
            self.remove_temp_file(file_obj)
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Incorrect CRS type: {crs}!'
                }).data
            )
        geocoding_request = None
        try:
            find_nearest = self.request.GET.get('find_nearest', 'false')
            find_nearest = find_nearest.lower() == 'true'
            geocoding_request = GeocodingRequest.objects.create(
                status=PENDING,
                submitted_on=timezone.now(),
                submitted_by=request.user,
                file_type=layer_type,
                parameters=(
                    f'({str(request_obj_id)},\'{spatial_query}\','
                    f'{dwithin_distance},\'{return_type_str}\',{admin_level},'
                    f'{str(find_nearest)},{self.request_type})'
                )
            )
            geocoding_request.file = file_obj
            geocoding_request.save(update_fields=['file'])
        except Exception as ex:
            if geocoding_request:
                # if fail to upload, remove the file
                geocoding_request.delete()
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Unable to save the file: {str(ex)}'
                }).data
            )
        finally:
            self.remove_temp_file(file_obj)

        task = process_geocoding_request.delay(geocoding_request.id)
        geocoding_request.task_id = task.id
        geocoding_request.save(update_fields=['task_id'])
        status_kwargs = {
            'uuid': str(request_obj_uuid),
            'request_id': str(geocoding_request.uuid)
        }
        status_url = reverse(self.status_url,
                             kwargs=status_kwargs,
                             request=request)
        status_url = request.build_absolute_uri(status_url)
        if not settings.DEBUG:
            # if not dev env, then replace with https
            status_url = status_url.replace('http://', 'https://')
        return Response(
            status=200,
            data={
                'request_id': str(geocoding_request.uuid),
                'status_url': status_url
            }
        )


class EntityBatchGeocodingStatus(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Check status of batch geocoding

    Task is completed when status is one of DONE, ERROR, or CANCELLED.
    """
    permission_classes = [DatasetDetailAccessPermission]
    request_type = GeocodingRequestType.DATASET
    result_url = 'v1:entity-get-result-batch-geocoding'

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    @swagger_auto_schema(
        operation_id='entity-check-status-batch-geocoding',
        tags=[OPERATION_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='Dataset UUID', type=openapi.TYPE_STRING
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
                        '{base_url}/api/v1/search/dataset/'
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
        _, request_obj_uuid = self.get_request_object(
            request, kwargs
        )
        request_uuid = kwargs.get('request_id')
        geocoding_request = get_object_or_404(GeocodingRequest,
                                              uuid=request_uuid)
        if geocoding_request.status in COMPLETED_STATUS:
            output_kwargs = {
                'uuid': str(request_obj_uuid),
                'request_id': str(geocoding_request.uuid)
            }
            output_url = reverse(self.result_url,
                                 kwargs=output_kwargs,
                                 request=request)
            output_url = request.build_absolute_uri(output_url)
            if not settings.DEBUG:
                # if not dev env, then replace with https
                output_url = output_url.replace('http://', 'https://')
            return Response(
                status=200,
                data={
                    'request_id': str(geocoding_request.uuid),
                    'status': geocoding_request.status,
                    'error': geocoding_request.errors,
                    'output_url': output_url
                }
            )
        return Response(
            status=200,
            data={
                'request_id': str(geocoding_request.uuid),
                'status': geocoding_request.status,
                'error': geocoding_request.errors,
                'output_url': None
            }
        )


class EntityBatchGeocodingResult(
    APILoggingMixin, APIView, DatasetDetailCheckPermission
):
    """
    Fetch geojson output of batch geocoding

    Return the geojson that contains geocoding output in one of the properties.
    """
    permission_classes = [DatasetDetailAccessPermission]

    def get_request_object(self, request, kwargs):
        dataset, _ = self.get_dataset_obj(request, kwargs)
        return dataset.id, dataset.uuid

    @swagger_auto_schema(
        operation_id='entity-get-result-batch-geocoding',
        tags=[OPERATION_ENTITY_TAG],
        manual_parameters=[
            openapi.Parameter(
                'uuid', openapi.IN_PATH,
                description='Dataset UUID', type=openapi.TYPE_STRING
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
        self.get_request_object(
            request, kwargs
        )
        request_uuid = kwargs.get('request_id')
        geocoding_request = get_object_or_404(GeocodingRequest,
                                              uuid=request_uuid)
        if geocoding_request.status == DONE and geocoding_request.output_file:
            return FileResponse(
                geocoding_request.output_file,
                as_attachment=True
            )
        return Response(
            status=404,
            data={
                'detail': 'Geocoding process is not completed yet.'
            }
        )


class FindEntityByUCode(APILoggingMixin, APIView):
    """
    Find entity by ucode.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer, GeojsonRenderer]
    id_type = 'ucode'

    def get_queryset(self, id_raw, dataset=None, dataset_view=None):
        ucode, version = parse_unique_code(id_raw)
        qs = GeographicalEntity.objects.select_related(
            'dataset', 'ancestor'
        ).filter(
            is_approved=True,
            unique_code=ucode,
            unique_code_version=version
        )

        if dataset:
            qs = qs.filter(dataset=dataset)
        if dataset_view:
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(dataset_view.uuid))
            qs = qs.filter(
                dataset=dataset_view.dataset,
                id__in=RawSQL(raw_sql, [])
            )

        return qs

    def get_serializer(self):
        if getattr(self, 'swagger_fake_view', False):
            return None
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        return (
            FindEntityByUcodeGeojsonSerializer if format == 'geojson'
            else FindEntityByUCodeSerializer
        )

    def generate_entity_query(
        self,
        entities,
        dataset_id,
        entity_type=None,
        admin_level=None
    ):
        # centroid, full_geom, no_geom. Default to no_geom
        geom_type = self.request.GET.get('geom', 'no_geom')
        geom_type = GeomReturnType.from_str(geom_type)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        entities, values, max_level, ids, names_max_idx = (
            do_generate_entity_query(
                entities, dataset_id, entity_type,
                admin_level, geom_type, format)
        )
        return entities.values(*values), max_level, ids, names_max_idx

    def generate_response(self, entities, context=None) -> Tuple[dict, dict]:
        """
        Return (response, response headers)
        """
        output = {}
        if entities is not None:
            output = (
                self.get_serializer()(entities.first(), context=context).data
            )
        return output, None

    def find_default_view(self, dataset: Dataset,
                          type: DatasetView.DefaultViewType,
                          country_unique_code = None):
        queryset = DatasetView.objects.filter(
            dataset=dataset,
            default_type=type
        )
        if country_unique_code:
            return queryset.filter(
                default_ancestor_code=country_unique_code
            ).first()
        return queryset.filter(
            default_ancestor_code__isnull=True
        ).first()

    def find_default_views(self, entity: GeographicalEntity):
        view_list = []
        dataset = entity.dataset
        country = entity.ancestor if entity.ancestor else entity
        # add all version default view
        view = self.find_default_view(
            dataset, DatasetView.DefaultViewType.ALL_VERSIONS)
        if view:
            view_list.append(view)
        # add all version country view
        view = self.find_default_view(
            dataset, DatasetView.DefaultViewType.ALL_VERSIONS,
            country.unique_code
        )
        if view:
            view_list.append(view)
        if not entity.is_latest:
            return view_list
        # add latest default view
        view = self.find_default_view(
            dataset, DatasetView.DefaultViewType.IS_LATEST
        )
        if view:
            view_list.append(view)
        # add latest country view
        view = self.find_default_view(
            dataset, DatasetView.DefaultViewType.IS_LATEST,
            country.unique_code
        )
        if view:
            view_list.append(view)
        return view_list

    def find_custom_views(self, entity: GeographicalEntity):
        view_list = []
        queryset = DatasetView.objects.filter(
            dataset=entity.dataset,
            default_type__isnull=True,
            default_ancestor_code__isnull=True
        )
        for view in queryset:
            if check_entity_in_view(view, entity.id):
                view_list.append(view)
        return view_list

    def check_external_permission_in_view(self, entity: GeographicalEntity,
                                          view: DatasetView):
        view_privacy_level = get_external_view_permission_privacy_level(
            self.request.user,
            view
        )
        return entity.privacy_level <= view_privacy_level

    def not_found_response(self):
        return Response(
            status=404,
            data=APIErrorSerializer({
                'detail': f'No entity with matching {self.id_type} found.'
            }).data
        )

    def get_views_dict(self, entity_qs, has_dataset_permission):
        results = {}
        for entity in entity_qs.iterator(chunk_size=1):
            view_list = []
            view_list.extend(self.find_default_views(entity))
            view_list.extend(self.find_custom_views(entity))
            if not has_dataset_permission:
                # check for external permission for each view
                view_list = [
                    view for view in view_list if
                    self.check_external_permission_in_view(entity, view)
                ]
            if len(view_list) > 0:
                view_list.sort(key=lambda x: x.name)
                results[entity.id] = view_list
        return results

    def find_dataset(self, entity_qs, request, kwargs):
        """Find dataset from the entity queryset or request object."""
        dataset = None
        if isinstance(self, DatasetDetailCheckPermission):
            dataset, _ = self.get_dataset_obj(
                request, kwargs
            )
        else:
            dataset = entity_qs.first().dataset
        
        return dataset

    @swagger_auto_schema(
        operation_id='search-entity-by-ucode',
        tags=[SEARCH_ENTITY_BASE_TAG],
        manual_parameters=[openapi.Parameter(
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
        entity_qs = GeographicalEntity.objects.none()
        id_raw = kwargs.get(self.id_type)
        try:
            entity_qs = self.get_queryset(id_raw)
        except ValueError:
            return Response(
                status=400,
                data=APIErrorSerializer({
                    'detail': f'Invalid {self.id_type} value {id_raw}.'
                }).data
            )
        if not entity_qs.exists():
            return self.not_found_response()
        dataset = self.find_dataset(entity_qs, request, kwargs)
        dataset_privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset
        )
        if dataset_privacy_level > 0:
            entity_qs = entity_qs.filter(
                privacy_level__lte=dataset_privacy_level
            )
            if not entity_qs.exists():
                return self.not_found_response()
        view_dict = self.get_views_dict(entity_qs, dataset_privacy_level > 0)
        if len(view_dict) == 0:
            return self.not_found_response()
        entity_qs = entity_qs.filter(id__in=view_dict.keys())
        entities, max_level, ids, names = self.generate_entity_query(
            entity_qs,
            dataset.id
        )
        response_data, response_headers = self.generate_response(
            entities,
            {
                'dataset_name': dataset.label,
                'dataset_uuid': dataset.uuid,
                'view_dict': view_dict,
                'max_level': max_level,
                'ids': ids,
                'names': names
            }
        )
        return Response(
            status=200,
            data=response_data,
            headers=response_headers
        )


class FindEntityByCUCode(FindEntityByUCode):
    """
    Find entity by concept ucode.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer, GeojsonRenderer]
    id_type = 'concept_ucode'

    def get_queryset(self, id_raw):
        return GeographicalEntity.objects.select_related(
            'dataset', 'ancestor'
        ).filter(
            is_approved=True,
            concept_ucode=id_raw
        ).order_by('unique_code_version')

    def generate_response(self, entities, context=None) -> Tuple[dict, dict]:
        """
        Return (response, response headers)
        """
        output = []
        if entities is not None:
            output = (
                self.get_serializer()(
                    entities,
                    context=context,
                    many=True
                ).data
            )
        return output, None

    @swagger_auto_schema(
        operation_id='search-entity-by-concept-ucode',
        tags=[SEARCH_ENTITY_BASE_TAG],
        manual_parameters=[openapi.Parameter(
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
        return super(FindEntityByCUCode, self).get(
            request, *args, **kwargs
        )


class FindEntityByUCodeDataset(FindEntityByUCode, DatasetDetailCheckPermission):
    """
    Find entity by ucode within a dataset.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [DatasetDetailAccessPermission]

    @swagger_auto_schema(
        operation_id='search-dataset-entity-by-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(FindEntityByUCodeDataset, self).get(
            request, *args, **kwargs
        )


class FindEntityByCUCodeDataset(FindEntityByCUCode, DatasetDetailCheckPermission):
    """
    Find entity by concept ucode within a dataset.

    Return single entity with its metadata and
    list of views that the entity belongs to.
    """
    permission_classes = [DatasetDetailAccessPermission]

    @swagger_auto_schema(
        operation_id='search-dataset-entity-by-concept-ucode',
        tags=[SEARCH_ENTITY_TAG],
        manual_parameters=[openapi.Parameter(
            'uuid', openapi.IN_PATH,
            description='Dataset UUID', type=openapi.TYPE_STRING
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
        return super(FindEntityByCUCodeDataset, self).get(
            request, *args, **kwargs
        )
