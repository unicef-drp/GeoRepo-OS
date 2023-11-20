from enum import Enum
from django.db.models import FilteredRelation, Q, F, Max
from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    MAIN_ENTITY_ID_LIST,
    EntityId,
    EntityName
)
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


def do_generate_entity_query(entities, dataset_uuid, entity_type=None,
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
        geographical_entity__dataset__uuid=dataset_uuid
    )
    names = EntityName.objects.filter(
        geographical_entity__is_approved=True,
        geographical_entity__dataset__uuid=dataset_uuid
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
    return entities.values(*values), max_level, ids, names_max_idx
