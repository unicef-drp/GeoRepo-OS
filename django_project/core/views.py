# coding=utf-8
"""
GeoRepo.

.. note:: Core views
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse

from core.utils.worker_health import get_worker_health


@staff_member_required
def worker_health(request):
    """Return celery worker health status as JSON for the admin badge.

    :param request: The current HTTP request.
    :type request: HttpRequest
    :return: JSON payload from :func:`get_worker_health`.
    :rtype: JsonResponse
    """
    return JsonResponse(get_worker_health())
