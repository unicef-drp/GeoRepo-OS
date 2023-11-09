import logging
from django.utils import timezone
from datetime import timedelta
from celery import shared_task
from georepo.models.geocoding_request import (
    GeocodingRequest
)
from georepo.models.search_id_request import (
    SearchIdRequest
)


logger = logging.getLogger(__name__)
REMOVE_AFTER_DAYS = 14


def clear_old_search_id_requests():
    datetime_filter = timezone.now() - timedelta(days=REMOVE_AFTER_DAYS)
    requests = SearchIdRequest.objects.filter(
        submitted_on__lte=datetime_filter
    )
    for request in requests:
        try:
            request.delete()
        except Exception as ex:
            logger.error(f'Failed to remove search id request {request}')
            logger.error(ex)


def clear_old_geocoding_requests():
    datetime_filter = timezone.now() - timedelta(days=REMOVE_AFTER_DAYS)
    requests = GeocodingRequest.objects.filter(
        submitted_on__lte=datetime_filter
    )
    for request in requests:
        try:
            request.delete()
        except Exception as ex:
            logger.error(f'Failed to remove geocoding request {request}')
            logger.error(ex)


@shared_task(name="remove_old_task_requests")
def remove_old_task_requests():
    clear_old_search_id_requests()
    clear_old_geocoding_requests()
