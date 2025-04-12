import os
import logging
import tempfile
import shutil
from uwsgi_tools.curl import curl
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from core.models.preferences import SitePreferences
from georepo.models.base_task_request import PROCESSING, DONE, ERROR
from dashboard.models.maintenance import StorageLog
from dashboard.models.blob_export import BlobExportRequest
from georepo.utils.azure_blob_storage import StorageContainerClient


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


@shared_task(name="run_blob_export_request")
def run_blob_export_request(id):
    """Run blob export request."""
    export_request = BlobExportRequest.objects.get(id=id)
    export_request.status = PROCESSING
    export_request.started_at = timezone.now()
    export_request.save()
    try:
        with tempfile.TemporaryDirectory() as working_dir:
            # get files and download to working dir
            export_request.download(working_dir)

            # zip the working_dir
            zip_path = os.path.join(
                '/tmp',
                f'{export_request.uuid}.zip'
            )
            shutil.make_archive(
                base_name=zip_path.replace('.zip', ''),
                format='zip',
                root_dir=working_dir,
            )

            if not os.path.exists(zip_path):
                raise FileNotFoundError(f'Zip file not found: {zip_path}')

            # upload the zip to blob storage
            export_request.output_path = (
                f'blob_exports/{export_request.uuid}.zip'
            )
            with open(zip_path, 'rb') as data:
                StorageContainerClient.upload_blob(
                    export_request.output_path,
                    data=data
                )

            # get size of the zip file
            export_request.size = os.path.getsize(zip_path)

            # remove the zip file
            os.remove(zip_path)

        export_request.status = DONE
    except Exception as e:
        logger.error(f'Error running blob export request: {e}', exc_info=True)
        export_request.status = ERROR
        export_request.errors = str(e)
    finally:
        export_request.finished_at = timezone.now()
        export_request.save()
