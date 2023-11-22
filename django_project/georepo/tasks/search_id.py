import logging
import traceback
import json
from ast import literal_eval as make_tuple
from celery import shared_task
from django.db.models.expressions import RawSQL
from django.db.models.functions import Concat
from django.db.models import Value as V, CharField
from django.utils import timezone
from django.core.files.base import ContentFile
from georepo.models.dataset_view import DatasetView
from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    GeographicalEntity
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
    do_generate_entity_query
)
from georepo.serializers.entity import (
    GeographicalEntitySerializer
)
from georepo.utils.uuid_helper import UUIDEncoder


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
    request.save(update_fields=['status', 'finished_at', 'progress',
                                'errors'])
    if is_success and results:
        output_name = f'{str(request.uuid)}.json'
        request.output_file.save(
            output_name,
            ContentFile(
                json.dumps(results, cls=UUIDEncoder).encode(
                    encoding='utf-8', errors='ignore'))
        )


def get_id_field_key(input_type: IdType | str):
    field_key = None
    if isinstance(input_type, IdType):
        field_key = f"id_{input_type.id}__value"
    elif input_type == CONCEPT_UCODE_ENTITY_ID:
        field_key = 'concept_ucode'
    elif input_type == CODE_ENTITY_ID:
        field_key = 'internal_code'
    elif input_type == UUID_ENTITY_ID:
        field_key = 'uuid_revision'
    elif input_type == CONCEPT_UUID_ENTITY_ID:
        field_key = 'uuid'
    elif input_type == UCODE_ENTITY_ID:
        field_key = 'ucode_filter'
    return field_key


def get_id_value(entity, input_type: IdType | str):
    field_key = get_id_field_key(input_type)
    return entity.get(field_key, None)


def do_search_id(view: DatasetView,
                 input_type: IdType | str,
                 max_privacy_level: int,
                 input_list):
    dataset = view.dataset
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        is_approved=True,
        privacy_level__lte=max_privacy_level
    )
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(view.uuid))
    entities = entities.filter(
        id__in=RawSQL(raw_sql, [])
    )
    entities, values, max_level, ids, names_max_idx = (
        do_generate_entity_query(entities, dataset.id)
    )
    entities = entities.annotate(
        ucode_filter=Concat('unique_code', V('_V'), 'unique_code_version',
                            output_field=CharField())
    )
    values.append('ucode_filter')
    id_field_key = get_id_field_key(input_type)
    id_filters = {
        f'{id_field_key}__in': input_list
    }
    entities = entities.filter(**id_filters)
    return entities.values(*values), max_level, ids, names_max_idx


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
    return_type = None
    if request.output_id_type:
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
        sanitized_inputs = [str(id_input) for id_input in request.input]
        entities, max_level, ids, names = do_search_id(
            view, input_type, max_privacy_level, sanitized_inputs)
        for entity in entities:
            id_input = get_id_value(entity, input_type)
            if id_input is None:
                continue
            search_output = None
            if return_type:
                search_output = get_id_value(entity, return_type)
            else:
                search_output = GeographicalEntitySerializer(
                    entity,
                    many=False,
                    context={
                        'max_level': max_level,
                        'ids': ids,
                        'names': names
                    }
                ).data
            if search_output is None:
                continue
            # add to results dict
            if id_input in results:
                results[id_input].append(search_output)
            else:
                results[id_input] = [search_output]
        # iterate original input to add missing item
        for id_input in sanitized_inputs:
            if str(id_input) in results:
                continue
            results[id_input] = []
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
