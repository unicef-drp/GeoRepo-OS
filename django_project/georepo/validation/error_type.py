from enum import Enum


class ErrorType(Enum):

    OVERLAPS = 'Overlaps'

    SELF_INTERSECTS = 'Self Intersects'

    DUPLICATE_GEOMETRIES = 'Duplicated Geometries'

    GEOMETRY_HIERARCHY = 'Not Within Parent'

    PARENT_ID_FIELD_ERROR = 'Parent Code Missing'

    ID_FIELDS_ERROR = 'Default Code Missing'

    NAME_FIELDS_ERROR = 'Default Name Missing'

    PARENT_CODE_HIERARCHY = 'Parent Missing'

    DUPLICATED_CODES = 'Duplicated Codes'
