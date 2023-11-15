import logging
import traceback
from ast import literal_eval as make_tuple
from celery import shared_task
from django.db import connection
from django.utils import timezone
from georepo.models.dataset_view import DatasetView
from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID
)
from georepo.models.base_task_request import (
    PROCESSING, DONE, ERROR
)
from georepo.models.search_id_request import (
    SearchIdRequest
)
from georepo.utils.permission import (
    get_view_permission_privacy_level
)
from georepo.utils.entity_query import (
    validate_return_type,
    get_column_id
)
from georepo.utils.unique_code import (
    parse_unique_code,
)


logger = logging.getLogger(__name__)


def start_processs_search_id_request(request: SearchIdRequest):
    request.status = PROCESSING
    request.started_at = timezone.now()
    request.progress = 0
    request.errors = None
    request.save(update_fields=['status', 'started_at', 'progress', 'errors'])


def end_process_search_id_request(request: SearchIdRequest,
                                  is_success, results, errors = None):
    request.status = DONE if is_success else ERROR
    request.finished_at = timezone.now()
    if not is_success:
        request.errors = errors
    else:
        request.progress = 100
        request.errors = None
        request.output = results
    request.save(update_fields=['status', 'finished_at', 'progress',
                                'errors', 'output'])


def get_query_cond_from_input_type(input_type: IdType | str,
                                   input_type_value: str):
    sql_conds = []
    sql_values = []
    if isinstance(input_type, IdType):
        sql_conds.append("gi2.value = %s")
        sql_values.append(input_type_value)
    elif input_type == CONCEPT_UCODE_ENTITY_ID:
        sql_conds.append("gg.concept_ucode = %s")
        sql_values.append(input_type_value)
    elif input_type == CODE_ENTITY_ID:
        sql_conds.append("gg.internal_code = %s")
        sql_values.append(input_type_value)
    elif input_type == UUID_ENTITY_ID:
        sql_conds.append("gg.uuid_revision = %s")
        sql_values.append(input_type_value)
    elif input_type == CONCEPT_UUID_ENTITY_ID:
        sql_conds.append("gg.uuid = %s")
        sql_values.append(input_type_value)
    elif input_type == UCODE_ENTITY_ID:
        ucode, version = parse_unique_code(input_type_value)
        sql_conds.append("gg.unique_code = %s")
        sql_conds.append("gg.unique_code_version = %s")
        sql_values.append(ucode)
        sql_values.append(version)
    return sql_conds, sql_values


def get_search_id_query(view: DatasetView, input_type: IdType | str,
                        output_type: IdType | str,
                        input_type_value: str,
                        max_privacy_level: int):
    other_joins = []
    sql_conds = [
        'gg.dataset_id = %s'
    ]
    query_values = [view.dataset.id]
    if isinstance(output_type, IdType):
        other_joins.append(
            """
            JOIN georepo_entityid gi
              ON gi.geographical_entity_id = gg.id
              AND gi.code_id={}
            """.format(output_type.id)
        )
    if isinstance(input_type, IdType):
        other_joins.append(
            """
            JOIN georepo_entityid gi2
              ON gi2.geographical_entity_id = gg.id
              AND gi2.code_id={}
            """.format(input_type.id)
        )
    sql_conds.append('gg.is_approved = true')
    sql_conds.append('gg.privacy_level <= %s')
    query_values.append(max_privacy_level)
    id_filter_conds, id_filter_values = get_query_cond_from_input_type(
        input_type, input_type_value)
    sql_conds.extend(id_filter_conds)
    query_values.extend(id_filter_values)
    sql_conds.append(
        "gg.id IN (SELECT id from \"{}\")".format(str(view.uuid))
    )
    where_sql = ' AND '.join(sql_conds)
    sql = (
        """
        select DISTINCT {column_id} as entity_id, gg.unique_code_version
        from georepo_geographicalentity gg
        {other_joins}
        {where_sql}
        ORDER BY gg.unique_code_version
        """
    ).format(
        column_id=get_column_id(output_type),
        other_joins=' '.join(other_joins),
        where_sql=f'where {where_sql}'
    )
    return sql, query_values


def do_search_id(view: DatasetView,
                 input_type: IdType | str,
                 output_type: IdType | str,
                 input_type_value: str,
                 max_privacy_level: int):
    sql, query_values = get_search_id_query(view, input_type, output_type,
                                            input_type_value,
                                            max_privacy_level)
    with connection.cursor() as cursor:
        cursor.execute(sql, query_values)
        rows = cursor.fetchall()
        return [row[0] for row in rows if row[0]]


@shared_task(name="process_search_id_request")
def process_search_id_request(request_id):
    request = SearchIdRequest.objects.get(id=request_id)
    # parse parameters
    params = make_tuple(request.parameters or '()')
    if len(params) < 1:
        logger.error(f'Invalid search id request parameters! {params}')
        end_process_search_id_request(
            request, False, None,
            f'Invalid search id request parameters! {params}')
        return
    # retrieve datasetView
    view = DatasetView.objects.get(id=params[0])
    max_privacy_level = get_view_permission_privacy_level(
        request.submitted_by,
        view.dataset,
        dataset_view=view
    )
    return_type = validate_return_type(request.output_id_type)
    if return_type is None:
        logger.error(
            'Invalid search id request '
            f'return type! {request.output_id_type}')
        end_process_search_id_request(
            request, False, None,
            'Invalid search id request '
            f'return type! {request.output_id_type}')
        return
    # validate input type
    input_type = validate_return_type(request.input_id_type)
    if input_type is None:
        logger.error(
            'Invalid search id request '
            f'input type! {request.input_id_type}')
        end_process_search_id_request(
            request, False, None,
            'Invalid search id request '
            f'input type! {request.input_id_type}')
        return
    start_processs_search_id_request(request)
    is_success = False
    results = {}
    errors = None
    try:
        for id_input in request.input:
            output = do_search_id(view, input_type, return_type,
                                  id_input, max_privacy_level)
            results[id_input] = output
        is_success = True
    except Exception as ex:
        print(traceback.format_exc())
        logger.error('Failed to process search id request!')
        logger.error(ex)
        errors = str(ex)
    finally:
        # end process
        end_process_search_id_request(
            request, is_success, results, errors)
