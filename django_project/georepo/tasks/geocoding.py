import logging
import time
import os
import json
from ast import literal_eval as make_tuple
from psycopg2.extras import execute_values
from celery import shared_task
from django.db import connection
from django.conf import settings
from django.contrib.gis.geos import Polygon, MultiPolygon
from django.utils import timezone
from georepo.models.dataset_view import DatasetView
from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    MAIN_ENTITY_ID_LIST
)
from georepo.models.geocoding_request import (
    GeocodingRequest, PROCESSING,
    DONE, ERROR
)
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)
from georepo.utils.layers import build_geom_object
from georepo.utils.permission import (
    get_view_permission_privacy_level
)


logger = logging.getLogger(__name__)
TEMP_SCHEMA = "temp"
TEMP_OUTPUT_GEOCODING_DIRECTORY = getattr(settings, 'FILE_UPLOAD_TEMP_DIR',
                                          '/home/web/media/tmp/geocoding')


def create_temp_schema():
    sql = (
        """create schema if not exists {schema_name}"""
    ).format(schema_name=TEMP_SCHEMA)
    with connection.cursor() as cursor:
        cursor.execute(sql)


def drop_temp_table(table_name):
    sql = (
        """DROP table if EXISTS {table_name}"""
    ).format(table_name=table_name)
    # with connection.cursor() as cursor:
    #     cursor.execute(sql)


def create_temp_table(table_name):
    drop_temp_table(table_name)
    sql = (
        """
        CREATE TABLE if not exists {table_name} (
            id serial4 NOT NULL,
            feature_idx int4 NOT NULL,
            geometry public.geometry(geometry, 4326) NOT NULL,
            properties jsonb NULL
        )
        """
    ).format(table_name=table_name)
    with connection.cursor() as cursor:
        cursor.execute(sql)


def insert_into_temp_table(table_name, data):
    sql = (
        """
        insert into {table_name} (feature_idx, geometry, properties)
        values %s
        """
    ).format(table_name=table_name)
    with connection.cursor() as cursor:
        execute_values(cursor, sql, data)


def validate_return_type(return_type: str) -> IdType | str:
        id_type = IdType.objects.filter(
            name__iexact=return_type
        )
        if id_type.exists():
            return id_type.first()
        # check whether id_type is uuid, Code
        if return_type in MAIN_ENTITY_ID_LIST:
            return return_type
        return None


def get_column_id(id_type: IdType | str):
    column_id = None
    if isinstance(id_type, IdType):
        column_id = 'gi.value'
    elif id_type == CONCEPT_UCODE_ENTITY_ID:
        column_id = 'gg.concept_ucode'
    elif id_type == CODE_ENTITY_ID:
        column_id = 'gg.internal_code'
    elif id_type == UUID_ENTITY_ID:
        column_id = 'gg.uuid_revision'
    elif id_type == CONCEPT_UUID_ENTITY_ID:
        column_id = 'gg.uuid'
    elif id_type == UCODE_ENTITY_ID:
        column_id = (
            """
            gg.unique_code || '_V' || CASE WHEN
            gg.unique_code_version IS NULL THEN 1 ELSE
            gg.unique_code_version END
            """
        )
    return column_id


def get_spatial_join(spatial_query: str, dwithin_distance: int):
    spatial_params = ''
    if spatial_query == 'ST_Intersects':
        spatial_params = 'ST_Intersects(s.geometry, gg.geometry)'
    elif spatial_query == 'ST_Within':
        spatial_params = 'ST_Within(s.geometry, gg.geometry)'
    elif spatial_query == 'ST_Within(ST_Centroid)':
        spatial_params = 'ST_Within(ST_Centroid(s.geometry), gg.geometry)'
    elif spatial_query == 'ST_DWithin':
        spatial_params = (
            'ST_DWithin(s.geometry, gg.geometry, {})'
        ).format(dwithin_distance)
    return spatial_params


def get_containment_check_query(view: DatasetView,
                                table_name: str,
                                spatial_query: str,
                                dwithin_distance: int,
                                max_privacy_level,
                                return_type: IdType | str,
                                admin_level: int):
    other_joins = []
    sql_conds = [
        'gg.dataset_id = %s'
    ]
    query_values = [view.dataset.id]

    if isinstance(return_type, IdType):
        other_joins.append(
            """
            LEFT JOIN georepo_entityid gi
              ON gi.geographical_entity_id = gg.id
            LEFT JOIN georepo_idtype gc ON gi.code_id = gc.id
            """
        )
        sql_conds.append('gc.name ilike %s')
        query_values.append(return_type)
    sql_conds.append('gg.level = %s')
    query_values.append(admin_level)
    sql_conds.append('gg.is_approved = true')
    sql_conds.append('gg.privacy_level <= %s')
    query_values.append(max_privacy_level)
    sql_conds.append(
        "gg.id IN (SELECT id from \"{}\")".format(str(view.uuid))
    )

    where_sql = ' AND '.join(sql_conds)
    sql = (
        """
        select s.id, s.feature_idx, {column_id} as result_id
        from {table_name} s
        left join georepo_geographicalentity gg on
        {spatial_join}
        {other_joins}
        {where_sql}
        ORDER BY s.id
        """
    ).format(
        table_name=table_name,
        column_id=get_column_id(return_type),
        spatial_join=get_spatial_join(spatial_query, dwithin_distance),
        other_joins=' '.join(other_joins),
        where_sql=f'where {where_sql}'
    )
    return sql, query_values


def do_containment_check(view: DatasetView,
                         table_name: str,
                         spatial_query: str,
                         dwithin_distance: int,
                         max_privacy_level,
                         return_type: IdType | str,
                         admin_level: int):
    sql, query_values = get_containment_check_query(
        view, table_name, spatial_query, dwithin_distance,
        max_privacy_level, return_type, admin_level
    )
    rows = []
    with connection.cursor() as cursor:
        cursor.execute(sql, query_values)
        rows = cursor.fetchall()


def delete_tmp_output_geocoding(geocoding_request: GeocodingRequest):
    tmp_file_path = os.path.join(
        TEMP_OUTPUT_GEOCODING_DIRECTORY,
        f"{str(geocoding_request.uuid)}.geojson"
    )
    if os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)


def start_process_geocoding_request(geocoding_request: GeocodingRequest):
    geocoding_request.status = PROCESSING
    geocoding_request.started_at = timezone.now()
    geocoding_request.progress = 0
    geocoding_request.save(update_fields=['status', 'started_at', 'progress'])
    create_temp_schema()
    table_name = geocoding_request.table_name(TEMP_SCHEMA)
    drop_temp_table(table_name)
    create_temp_table(table_name)
    if not os.path.exists(TEMP_OUTPUT_GEOCODING_DIRECTORY):
        os.makedirs(TEMP_OUTPUT_GEOCODING_DIRECTORY)
    return table_name


def end_process_geocoding_request(geocoding_request: GeocodingRequest,
                                  is_success, output_file,
                                  feature_count, errors = None):
    geocoding_request.status = DONE if is_success else ERROR
    geocoding_request.finished_at = timezone.now()
    geocoding_request.feature_count = feature_count
    if not is_success:
        geocoding_request.errors = errors
    else:
        geocoding_request.progress = 100
        geocoding_request.errors = None
        geocoding_request.output_file = output_file
    geocoding_request.save(update_fields=['status', 'finished_at',
                                          'progress', 'feature_count',
                                          'errors', 'output_file'])
    table_name = geocoding_request.table_name(TEMP_SCHEMA)
    drop_temp_table(table_name)
    delete_tmp_output_geocoding(geocoding_request)


def geocoding_request_on_delete(geocoding_request: GeocodingRequest):
    # delete table if exists
    table_name = geocoding_request.table_name(TEMP_SCHEMA)
    drop_temp_table(table_name)
    # delete temp output if any
    delete_tmp_output_geocoding(geocoding_request)


def process_geocoding_request(request_id):
    geocoding_request = GeocodingRequest.objects.get(id=request_id)
    # parse parameters
    params = make_tuple(geocoding_request.parameters or '()')
    if len(params) < 5:
        logger.error(f'Invalid geocoding request parameters! {params}')
        end_process_geocoding_request(
            geocoding_request, False, None, 0,
            f'Invalid geocoding request parameters! {params}')
        return
    # retrieve datasetView
    view = DatasetView.objects.get(id=params[0])
    max_privacy_level = get_view_permission_privacy_level(
        geocoding_request.submitted_by,
        view.dataset,
        dataset_view=view
    )
    spatial_query = params[1]
    dwithin_distance = int(params[2])
    return_type_str = params[3]
    admin_level = int(params[4])
    return_type = validate_return_type(return_type_str)
    if return_type is None:
        logger.error(f'Invalid geocoding request return type! {return_type_str}')
        end_process_geocoding_request(
            geocoding_request, False, None, 0,
            f'Invalid geocoding request return type! {return_type_str}')
        return
    table_name = start_process_geocoding_request(geocoding_request)
    # read file
    feature_count = 0
    with open_collection_by_file(geocoding_request.file,
                                 geocoding_request.file_type) as features:
        data = []
        feature_count = 0
        for feature_idx, feature in enumerate(features):
            geom_str = json.dumps(feature['geometry'])
            geom = build_geom_object(geom_str)
            if geom is None:
                continue
            if geom and isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            properties = (
                feature['properties'] if 'properties' in feature else {}
            )
            data.append((
                feature_idx,
                geom.ewkt,
                json.dumps(properties)   
            ))
            feature_count += 1
            if len(data) == 100:
                insert_into_temp_table(table_name, data)
                data.clear()
        if len(data) > 0:
            insert_into_temp_table(table_name, data)
        delete_tmp_shapefile(features.path)
    # do containment check
    is_success = False
    output_file = None
    errors = None
    sql, query_values = get_containment_check_query(
        view, geocoding_request.table_name(TEMP_SCHEMA),
        spatial_query, dwithin_distance, max_privacy_level,
        return_type, admin_level
    )
    print(sql)
    print('*****')
    print(query_values)
    # end process
    end_process_geocoding_request(
        geocoding_request, is_success, output_file, feature_count, errors)
