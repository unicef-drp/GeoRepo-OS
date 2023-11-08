from georepo.models.id_type import IdType
from georepo.models.entity import (
    UUID_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID,
    CODE_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID,
    MAIN_ENTITY_ID_LIST
)


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


def get_return_type_key(return_type: IdType | str):
    if isinstance(return_type, IdType):
        return return_type.name
    return return_type
