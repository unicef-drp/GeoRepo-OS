from enum import Enum


class ErrorType(Enum):

    BOUNDARY_TYPE_ERROR = 'Boundary Type Missing/Invalid'

    INVALID_PRIVACY_LEVEL = 'Invalid Privacy Level'

    PRIVACY_LEVEL_ERROR = 'Privacy Level Missing'

    UPGRADED_PRIVACY_LEVEL = 'Upgraded Privacy Level'


ALLOWABLE_ERROR_TYPES = [
    ErrorType.UPGRADED_PRIVACY_LEVEL
]


SUPERADMIN_BYPASS_ERROR = [
    ErrorType.PRIVACY_LEVEL_ERROR,
    ErrorType.INVALID_PRIVACY_LEVEL,
    ErrorType.UPGRADED_PRIVACY_LEVEL
]
