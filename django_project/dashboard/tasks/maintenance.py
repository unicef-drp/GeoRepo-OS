import os
import re
import logging
import tempfile
import shutil
from uwsgi_tools.curl import curl
from celery import shared_task
from django.conf import settings
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


def delete_numbered_log_files(parent_dir, max_depth=2, dry_run=True):
    """
    Delete all numbered log files (e.g., worker.log.1, app.log.2, etc.).

    :param parent_dir: Parent directory to search for numbered log files
    :type parent_dir: str
    :param max_depth: Maximum depth to traverse subdirectories, defaults to 2
    :type max_depth: int, optional
    :param dry_run: If True, only report what would be deleted
        without actually deleting, defaults to True
    :type dry_run: bool, optional
    :return: Tuple containing (deleted_count, total_size_freed,
        deleted_files_list)
    :rtype: tuple[int, int, list[str]]
    :raises OSError: If there are permission issues accessing directories
    :raises PermissionError: If there are permission issues deleting files

    :Example:

    >>> # Dry run first (safe - doesn't delete anything)
    >>> count, size, files = delete_numbered_log_files('/logs', max_depth=2,
        dry_run=True)
    >>> print(f"Would delete {count} files, {size / (1024*1024):.2f} MB")
    >>>
    >>> # Actually delete the files
    >>> count, size, files = delete_numbered_log_files('/logs', max_depth=2,
        dry_run=False)
    >>> print(f"Deleted {count} files, freed {size / (1024*1024):.2f} MB")
    """
    deleted_files = []
    total_size = 0
    deleted_count = 0

    # Pattern to match numbered log files: .log.1, .log.2, .txt.1, etc.
    # Limit to 1-3 digits to avoid matching year-suffixed
    # files (e.g. .log.2024)
    numbered_pattern = re.compile(r'\.(log|txt|status)\.\d{1,3}$')

    try:
        for entry in os.scandir(parent_dir):
            if entry.is_file():
                # Check if filename matches numbered log pattern
                if numbered_pattern.search(entry.name):
                    try:
                        stat = entry.stat()
                        file_size = stat.st_size
                        if dry_run:
                            logger.info(
                                f"[DRY RUN] Would delete: {entry.path} "
                                f"({file_size} bytes)"
                            )
                        else:
                            os.remove(entry.path)
                            logger.info(
                                f"Deleted: {entry.path} ({file_size} bytes)"
                            )

                        deleted_files.append(entry.path)
                        total_size += file_size
                        deleted_count += 1
                    except (OSError, PermissionError) as e:
                        logger.error(
                            f"Error deleting {entry.path}: {e}",
                            exc_info=True
                        )
                        continue

            elif entry.is_dir() and max_depth > 0:
                # Recursively delete in subdirectories
                try:
                    sub_count, sub_size, sub_files = delete_numbered_log_files(
                        entry.path, max_depth - 1, dry_run
                    )
                    deleted_count += sub_count
                    total_size += sub_size
                    deleted_files.extend(sub_files)
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError) as e:
        logger.error(
            f"Error accessing directory {parent_dir}: {e}", exc_info=True
        )

    return deleted_count, total_size, deleted_files


@shared_task(name="cleanup_tmp_directory")
def cleanup_tmp_directory(threshold_override=None):
    """Cleanup task for /tmp directory to remove old numbered log files.

    :param threshold_override: Override the critical threshold percentage.
        If None, uses STORAGE_CRITICAL_THRESHOLD from settings (default 90).
    :type threshold_override: int or float or None
    :return: Dict with total deleted file count and total size freed in bytes.
    :rtype: dict
    """
    critical_threshold = (
        threshold_override
        if threshold_override is not None
        else getattr(settings, 'STORAGE_CRITICAL_THRESHOLD', 90)
    )
    storage_paths = ['/tmp']
    total_deleted_count = 0
    total_freed_size = 0
    for path in storage_paths:
        if not path or not os.path.exists(path):
            continue

        disk_usage = shutil.disk_usage(path)
        usage_percent = round(
            (disk_usage.used / disk_usage.total) * 100, 2
        )

        if usage_percent > critical_threshold:
            logger.error(
                f"Storage '{path}' CRITICAL: {usage_percent:.2f}% "
                f"used at {path}"
            )
            # Perform cleanup of numbered log files
            deleted_count, freed_size, deleted_files = (
                delete_numbered_log_files(
                    path, max_depth=2, dry_run=False
                )
            )
            total_deleted_count += deleted_count
            total_freed_size += freed_size
            logger.info(
                f"Deleted {deleted_count} numbered log files, "
                f"freed {freed_size / (1024*1024):.2f} MB in '{path}'"
            )

    return {
        'deleted_count': total_deleted_count,
        'freed_size_bytes': total_freed_size,
    }
