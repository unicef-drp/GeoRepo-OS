from enum import Enum
import math
from dateutil.parser import parse
from datetime import datetime
from django.db.models import FilteredRelation, Q, F, Max
from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    MAIN_ENTITY_ID_LIST,
    EntityId,
    EntityName,
    GeographicalEntity
)
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.utils.custom_geo_functions import (
    ForcePolygonCCW
)


class GeomReturnType(Enum):
    NO_GEOM = 'no_geom'
    FULL_GEOM = 'full_geom'
    CENTROID = 'centroid'

    @staticmethod
    def from_str(label):
        try:
            return GeomReturnType(label)
        except KeyError:
            pass
        return None


def validate_return_type(return_type: str) -> IdType | str:
    id_type = IdType.objects.filter(
        name__iexact=return_type
    )
    if id_type.exists():
        return id_type.first()
    # check whether id_type is uuid, Code
    if return_type:
        return_type_str = return_type.lower()
        if return_type_str in MAIN_ENTITY_ID_LIST:
            return return_type_str
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
    elif id_type is None:
        column_id = 'gg.id'
    return column_id


def get_return_type_key(return_type: IdType | str):
    if isinstance(return_type, IdType):
        return return_type.name
    return return_type


def do_generate_entity_query(entities, dataset_id, entity_type=None,
                             admin_level=None,
                             geom_type=GeomReturnType.NO_GEOM,
                             format='json'):
    # initial fields to select
    values = [
        'id', 'label', 'internal_code',
        'unique_code', 'unique_code_version',
        'uuid', 'uuid_revision',
        'type__label', 'level', 'start_date', 'end_date',
        'is_latest', 'admin_level_name', 'concept_ucode', 'bbox'
    ]
    if geom_type == GeomReturnType.FULL_GEOM or format == 'geojson':
        entities = entities.annotate(
            rhr_geom=ForcePolygonCCW(F('geometry'))
        )
        values.append('rhr_geom')
    elif geom_type == GeomReturnType.CENTROID:
        values.append('centroid')
    # retrieve all ids+names in current dataset
    ids = EntityId.objects.filter(
        geographical_entity__is_approved=True,
        geographical_entity__dataset_id=dataset_id
    )
    names = EntityName.objects.filter(
        geographical_entity__is_approved=True,
        geographical_entity__dataset_id=dataset_id
    )
    if entity_type:
        ids = ids.filter(
            geographical_entity__type=entity_type.id
        )
        names = names.filter(
            geographical_entity__type=entity_type.id
        )
    if admin_level is not None:
        ids = ids.filter(
            geographical_entity__level=admin_level
        )
        names = names.filter(
            geographical_entity__level=admin_level
        )
    ids = ids.order_by('code').values(
        'code__id', 'code__name', 'default'
    ).distinct('code__id')
    # conditional join to entity id for each id
    for id in ids:
        field_key = f"id_{id['code__id']}"
        annotations = {
            field_key: FilteredRelation(
                'entity_ids',
                condition=Q(entity_ids__code__id=id['code__id'])
            )
        }
        entities = entities.annotate(**annotations)
        values.append(f'{field_key}__value')
    # get max idx in the names
    names_max_idx = names.aggregate(
        Max('idx')
    )
    if names_max_idx['idx__max'] is not None:
        for name_idx in range(names_max_idx['idx__max'] + 1):
            field_key = f"name_{name_idx}"
            annotations = {
                field_key: FilteredRelation(
                    'entity_names',
                    condition=Q(
                        entity_names__idx=name_idx
                    )
                )
            }
            entities = entities.annotate(**annotations)
            values.append(f'{field_key}__name')
            values.append(f'{field_key}__language__code')
            values.append(f'{field_key}__label')
    # find max level to build query for the parent's code
    max_level = 0
    max_level_entity = entities.values('level').order_by(
        'level'
    ).last()
    if max_level_entity:
        max_level = max_level_entity['level']
    related = ''
    for i in range(max_level):
        related = related + (
            '__parent' if i > 0 else 'parent'
        )
        # fetch parent's default code
        values.append(f'{related}__internal_code')
        values.append(f'{related}__unique_code')
        values.append(f'{related}__unique_code_version')
        values.append(f'{related}__level')
        values.append(f'{related}__type__label')
    entities = entities.order_by('level', 'unique_code_version',
                                 'unique_code', 'id')
    return entities, values, max_level, ids, names_max_idx


def do_generate_fuzzy_query(view: DatasetView, search_text: str,
                            max_privacy_level: int, page: int,
                            page_size: int):
    dataset: Dataset = view.dataset
    select_dicts = {
        'id': 'gg.id',
        'matching_name': 'ename.name',
        'similarity': 'word_similarity(%s, ename.name)',
        'label': 'gg.label',
        'internal_code': 'gg.internal_code',
        'unique_code': 'gg.unique_code',
        'unique_code_version': 'gg.unique_code_version',
        'uuid': 'gg.uuid',
        'uuid_revision': 'gg.uuid_revision',
        'type__label': 'ge.label',
        'level': 'gg.level',
        'start_date': 'gg.start_date',
        'end_date': 'gg.end_date',
        'is_latest': 'gg.is_latest',
        'admin_level_name': 'gg.admin_level_name',
        'concept_ucode': 'gg.concept_ucode',
        'bbox': 'gg.bbox'
    }
    other_joins = []
    # add code/id
    ids = EntityId.objects.filter(
        geographical_entity__is_approved=True,
        geographical_entity__dataset=dataset
    ).order_by('code').values(
        'code__id', 'code__name', 'default'
    ).distinct('code__id')
    for id in ids:
        field_key = f"id_{id['code__id']}"
        other_joins.append(
            f"left join georepo_entityid {field_key} on (gg.id={field_key}."
            f"geographical_entity_id and {field_key}."
            f"code_id={id['code__id']})"
        )
        select_dicts[f'{field_key}__value'] = f'{field_key}.value'
    # add other names
    names = EntityName.objects.filter(
        geographical_entity__is_approved=True,
        geographical_entity__dataset=dataset
    )
    names_max_idx = names.aggregate(
        Max('idx')
    )
    if names_max_idx['idx__max'] is not None:
        for name_idx in range(names_max_idx['idx__max'] + 1):
            field_key = f"name_{name_idx}"
            other_joins.append(
                f"left join georepo_entityname {field_key} on "
                f"(gg.id={field_key}.geographical_entity_id and "
                f"{field_key}.idx={name_idx})"
            )
            other_joins.append(
                f"left join georepo_language {field_key}_lang on "
                f"({field_key}.language_id={field_key}_lang.id)"
            )
            select_dicts[f'{field_key}__name'] = f'{field_key}.name'
            select_dicts[f'{field_key}__label'] = f'{field_key}.label'
            select_dicts[f'{field_key}__language__code'] = (
                f'{field_key}_lang.code'
            )
    # add parents
    max_level = 0
    max_level_entity = GeographicalEntity.objects.filter(
        is_approved=True,
        dataset=dataset
    ).values('level').order_by(
        'level'
    ).last()
    if max_level_entity:
        max_level = max_level_entity['level']
        for i in range(max_level):
            field_key = f"parent_{i}"
            prev_field = (
                f"parent_{i-1}" if i > 0 else "gg"
            )
            other_joins.append(
                f"left join georepo_geographicalentity {field_key} on "
                f"({field_key}.id={prev_field}.parent_id)"
            )
            other_joins.append(
                f"left join georepo_entitytype {field_key}_type on "
                f"({field_key}.type_id={field_key}_type.id)"
            )
            select_dicts[f'{field_key}__internal_code'] = (
                f'{field_key}.internal_code'
            )
            select_dicts[f'{field_key}__unique_code'] = (
                f'{field_key}.unique_code'
            )
            select_dicts[f'{field_key}__unique_code_version'] = (
                f'{field_key}.unique_code_version'
            )
            select_dicts[f'{field_key}__level'] = f'{field_key}.level'
            select_dicts[f'{field_key}__type__label'] = (
                f'{field_key}_type.label'
            )
    sql_select = 'SELECT '
    selects = []
    for key, value in select_dicts.items():
        selects.append(f'{value} as {key}')
    sql_select = (
        sql_select + ', '.join(selects)
    )
    sql_template = (
        """
        {sql_select}
        FROM georepo_entityname ename
        inner join georepo_geographicalentity gg
        on gg.id=ename.geographical_entity_id
        inner join georepo_entitytype ge on ge.id=gg.type_id
        {other_joins}
        WHERE %s <%% ename.name and gg.dataset_id = {dataset_id} and
        gg.privacy_level <= {max_privacy_level}
        and gg.id in (SELECT id from "{view_uuid}")
        {order_by}
        """
    )
    offset = (page - 1) * page_size
    pagination = f'OFFSET {offset} LIMIT {page_size}'
    sql = sql_template.format(
        sql_select=sql_select,
        other_joins=' '.join(other_joins),
        dataset_id=dataset.id,
        max_privacy_level=max_privacy_level,
        view_uuid=str(view.uuid),
        order_by=f'ORDER BY similarity DESC {pagination}'
    )
    count_sql = sql_template.format(
        sql_select='SELECT COUNT(*)',
        other_joins=' '.join(other_joins),
        dataset_id=dataset.id,
        max_privacy_level=max_privacy_level,
        view_uuid=str(view.uuid),
        order_by=''
    )
    query_values = [search_text, search_text]
    count_query_values = [search_text]
    return {
        'sql': sql,
        'count_sql': count_sql,
        'query_values': query_values,
        'count_query_values': count_query_values,
        'select_keys': list(select_dicts.keys()),
        'max_level': max_level,
        'ids': ids,
        'names_max_idx': names_max_idx
    }


def normalize_attribute_name(name: str, name_idx: int) -> str:
    """Ensure attribute name must be max 10 chars."""
    suffix_length = int(math.log10(name_idx + 1)) + 2
    label_for_current_val = name
    if len(label_for_current_val) + suffix_length > 10:
        # truncate name_label so fit to shapefile
        n = len(label_for_current_val) + suffix_length - 10
        label_for_current_val = label_for_current_val[:-n]
    return '{label}_{label_idx}'.format(
        label=label_for_current_val,
        label_idx=name_idx + 1
    )


def validate_datetime(value: str) -> datetime:
    res = None
    if value is None:
        return res
    try:
        res = parse(value)
    except ValueError:
        pass
    return res
