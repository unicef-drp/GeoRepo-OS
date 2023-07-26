from enum import Enum
from collections import OrderedDict


LEVEL = 'Level'
ENTITY_CODE = 'Entity Code'
ENTITY_NAME = 'Entity Name'
ERROR_CHECK = '1'


class ErrorType(Enum):
    # geometry validity checks
    SELF_INTERSECTS = 'Self Intersects'

    SELF_CONTACTS = 'Self Contacts'

    DUPLICATE_NODES = 'Duplicate Nodes'

    DEGENERATE_POLYGON = 'Polygon with less than 4 nodes'

    # geometry topology checks
    DUPLICATE_GEOMETRIES = 'Duplicated Geometries'

    WITHIN_OTHER_FEATURES = 'Feature within other features'

    OVERLAPS = 'Overlaps'

    GAPS = 'Gaps'

    GEOMETRY_HIERARCHY = 'Not Within Parent'

    # attributes checks
    PARENT_ID_FIELD_ERROR = 'Parent Code Missing'

    ID_FIELDS_ERROR = 'Default Code Missing'

    NAME_FIELDS_ERROR = 'Default Name Missing'

    DUPLICATED_CODES = 'Duplicated Codes'

    INVALID_PRIVACY_LEVEL = 'Invalid Privacy Level'

    PRIVACY_LEVEL_ERROR = 'Privacy Level Missing'

    PARENT_CODE_HIERARCHY = 'Parent Missing'

    UPGRADED_PRIVACY_LEVEL = 'Upgraded Privacy Level'


ALLOWABLE_ERROR_TYPES = [
    ErrorType.SELF_INTERSECTS,
    ErrorType.SELF_CONTACTS,
    ErrorType.DUPLICATE_NODES,
    ErrorType.GAPS,
    ErrorType.UPGRADED_PRIVACY_LEVEL
]

SUPERADMIN_BYPASS_ERROR = [
    ErrorType.SELF_INTERSECTS,
    ErrorType.DUPLICATE_NODES,
    ErrorType.DEGENERATE_POLYGON,
    ErrorType.OVERLAPS,
    ErrorType.GAPS,
    ErrorType.DUPLICATE_GEOMETRIES,
    ErrorType.WITHIN_OTHER_FEATURES,
    ErrorType.GEOMETRY_HIERARCHY,
    ErrorType.PRIVACY_LEVEL_ERROR,
    ErrorType.INVALID_PRIVACY_LEVEL,
    ErrorType.UPGRADED_PRIVACY_LEVEL
]


def create_layer_error(level: int, code: str = '', name: str = ''):
    """Create dictionary to store error report for each feature."""
    layer_error = OrderedDict({
        LEVEL: level,
        ENTITY_CODE: code,
        ENTITY_NAME: name
    })
    for error_type in ErrorType:
        layer_error[error_type.value] = ''
    return layer_error


def create_level_error_report(level: int, entity_type: str,
                              entity_type_label: str):
    """Create dictionary to store error report for features in level."""
    level_error_report = OrderedDict({
        LEVEL: level,
        entity_type: entity_type_label,
    })
    for error_type in ErrorType:
        level_error_report[error_type.value] = 0
    return level_error_report
