import json
import math
from typing import Tuple
from datetime import datetime
from dateutil.parser import isoparse
from django.db import connection
from django.http import Http404
from django.core.exceptions import PermissionDenied
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from django.contrib.gis.geos import GEOSGeometry
from core.models.preferences import SitePreferences
from django.db.models import FilteredRelation, Q, Value, F, IntegerField
from django.db.models.functions import Replace, Greatest
from django.contrib.postgres.search import TrigramWordSimilarity
from django.core.paginator import Paginator
from rest_framework.renderers import JSONRenderer
from georepo.utils.renderers import GeojsonRenderer
from georepo.utils.permission import (
    DatasetDetailAccessPermission,
    get_view_permission_privacy_level
)

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
    GeographicalGeojsonSerializer
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
    get_unique_code
)
from georepo.utils.url_helper import get_ucode_from_url_path
from georepo.utils.uuid_helper import get_uuid_value
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import (
    SEARCH_ENTITY_TAG,
    OPERATION_ENTITY_TAG,
    CONTROLLED_LIST_TAG
)
from georepo.utils.api_parameters import common_api_params
from georepo.utils.entity_query import (
    GeomReturnType,
    do_generate_entity_query
)


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
class EntityIdList(APIView):
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


class EntityBoundingBox(APIView, DatasetDetailCheckPermission):
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
        geom = None
        if req_label in MAIN_ENTITY_ID_LIST:
            entity = GeographicalEntity.objects.filter(
                is_latest=True,
                is_approved=True,
                dataset=dataset,
                privacy_level__lte=max_privacy_level
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
                geographical_entity__is_latest=True,
                geographical_entity__is_approved=True,
                geographical_entity__dataset=dataset,
                geographical_entity__privacy_level__lte=max_privacy_level
            ).select_related(
                'geographical_entity'
            ).order_by('geographical_entity__id').last()
            if entity_id:
                geom = entity_id.geographical_entity.geometry
        if not geom:
            raise Http404('No GeographicalEntity matches the given query.')
        return Response(
            geom.extent
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
class EntityTypeList(APIView):
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


class EntityContainmentCheck(APIView, DatasetDetailCheckPermission):
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


class EntitySearchBase(ApiCache, DatasetDetailCheckPermission):
    cache_model = Dataset
    renderer_classes = [JSONRenderer, GeojsonRenderer]
    # [Dataset, View]
    search_source = 'Dataset'
    permission_classes = [DatasetDetailAccessPermission]

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
        dataset_uuid,
        entity_type=None,
        admin_level=None
    ):
        # centroid, full_geom, no_geom. Default to no_geom
        geom_type = self.request.GET.get('geom', 'no_geom')
        geom_type = GeomReturnType.from_str(geom_type)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        return do_generate_entity_query(entities, dataset_uuid, entity_type,
                                        admin_level, geom_type, format)

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
        if entities is not None:
            # set pagination
            paginator = Paginator(entities, page_size)
            total_page = math.ceil(paginator.count / page_size)
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
                'page_size': page_size
            }
        return {
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
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
            str(dataset.uuid),
            entity_type=entity_type,
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

    def generate_response(self, entities, context=None):
        # pagination parameter
        page = int(self.request.GET.get('page', '1'))
        page_size = get_page_size(self.request)
        # json or geojson. Default to json
        format = self.request.GET.get('format', 'json')
        output = []
        total_page = 0
        if entities is not None:
            # set pagination
            paginator = Paginator(entities, page_size)
            total_page = math.ceil(paginator.count / page_size)
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
                    'page_size': page_size
                }
            )
        return Response(data={
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
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
        is_latest = request.GET.get('latest', None)
        if is_latest is not None:
            is_latest = is_latest.lower() == 'true'
            entities = entities.filter(
                is_latest=is_latest
            )
        entities, max_level, ids, names = self.generate_entity_query(
            entities,
            str(dataset.uuid)
        )
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
    Find closest geographical entity

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
        is_latest = request.GET.get('latest', None)
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
            str(dataset.uuid)
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
    Find list of geographical entity by level and parent ucode in dataset

    Retrieve list of geographical entity in dataset \
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
            str(dataset.uuid)
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
            str(dataset.uuid)
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
