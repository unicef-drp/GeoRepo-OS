from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied as RestPermissionDenied
)
from django.core.exceptions import (
    ValidationError,
    PermissionDenied
)
from django.http import Http404
from django.db.utils import (
    ProgrammingError
)
import logging
import traceback


logger = logging.getLogger(__name__)

EXCLUDED_EXCEPTIONS = (
    Http404,
    PermissionDenied,
    NotAuthenticated,
    RestPermissionDenied,
)


def log_exception(exc):
    logger.error(f'Unexpected exception occured: {type(exc).__name__}')
    logger.error(exc)
    logger.error(traceback.format_exc())


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response and response.status_code == 500:
        log_exception(exc)
        response.status_code = 400
        response.data['detail'] = str(exc)
    elif isinstance(exc, ValidationError):
        log_exception(exc)
        response = Response(
            {
                'detail': str(exc)
            },
            status=400,
            headers={}
        )
    elif isinstance(exc, ProgrammingError):
        log_exception(exc)
        response = Response(
            {
                'detail': str(exc)
            },
            status=400,
            headers={}
        )
    elif response is None:
        log_exception(exc)
        # catch any other exception
        response = Response(
            {
                'detail': str(exc)
            },
            status=400,
            headers={}
        )
    elif not isinstance(exc, EXCLUDED_EXCEPTIONS):
        log_exception(exc)

    return response
