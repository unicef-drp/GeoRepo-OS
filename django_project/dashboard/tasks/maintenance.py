import logging
from uwsgi_tools.curl import curl
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from core.models.preferences import SitePreferences
from dashboard.models.maintenance import StorageLog


logger = logging.getLogger(__name__)
REMOVE_AFTER_DAYS = 14


@shared_task(name="trigger_storage_checker_api", ignore_result=True)
def trigger_storage_checker_api():
    pref = SitePreferences.preferences()
    if not pref.storage_checker_config:
        return
    api_key = pref.storage_checker_config.get('api_key', None)
    user = pref.storage_checker_config.get('user', None)
    host = 'django:8080'
    endpoint_url = pref.storage_checker_config.get(
        'endpoint_url',
        '/api/maintenance/check-storage-usage/'
    )
    if api_key is None or user is None:
        return

    headers = (
        f'Authorization: Bearer {api_key}',
        f'GEOREPO_USER_KEY: {user}',
    )
    curl(host, endpoint_url, headers=headers)


@shared_task(name="clean_old_storage_log")
def clean_old_storage_log():
    datetime_filter = timezone.now() - timedelta(days=REMOVE_AFTER_DAYS)
    StorageLog.objects.filter(
        date_time__lte=datetime_filter
    ).delete()
