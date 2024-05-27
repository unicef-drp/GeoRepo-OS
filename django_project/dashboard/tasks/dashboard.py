from celery import shared_task
import logging
import os
import shutil
import csv
from io import StringIO
from django.core.files.base import ContentFile
from django.conf import settings
from dashboard.models.temp_usage import TempUsage
from georepo.utils.directory_helper import (
    get_folder_size,
    convert_size
)
from georepo.utils.azure_blob_storage import DirectoryClient


logger = logging.getLogger(__name__)


@shared_task(name="clear_dashboard_dataset_session")
def clear_dashboard_dataset_session():
    from datetime import datetime, timedelta
    from django.db import connection
    # clear entities user config session that is older than 7 days
    # exclude last config for each user+dataset
    sql = (
        'DELETE FROM dashboard_entitiesuserconfig '
        'WHERE id NOT IN('
        '    select max(de.id) '
        '    from dashboard_entitiesuserconfig de '
        '    group by de.user_id, de.dataset_id '
        '    ) AND '
        'updated_at < %s'
    )
    datetime_filter = datetime.now() - timedelta(days=7)
    with connection.cursor() as cursor:
        cursor.execute(sql, [datetime_filter])


@shared_task(name="calculate_temp_directory")
def calculate_temp_directory():
    total_size = 0
    directory_path = settings.MEDIA_ROOT
    if not os.path.exists(directory_path):
        return
    rows = []
    for path, dirs, files in os.walk(directory_path):
        for dir in dirs:
            fp = os.path.join(path, dir)
            fp_size = get_folder_size(fp)
            total_size += fp_size
            rows.append([dir, convert_size(fp_size)])
        break
    tmp_directory_path = '/tmp'
    if os.path.exists(tmp_directory_path):
        for path, dirs, files in os.walk(tmp_directory_path):
            for dir in dirs:
                fp = os.path.join(path, dir)
                fp_size = get_folder_size(fp)
                total_size += fp_size
                rows.append([dir, convert_size(fp_size)])
            break
    row = ["Name", "Size"]
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(row)
    csv_writer.writerows(rows)
    csv_file = ContentFile(csv_buffer.getvalue().encode('utf-8'))
    temp_usage = TempUsage()
    temp_usage.total_size = total_size
    temp_usage.report_file.save('report_file_usage.csv', csv_file)
    temp_usage.save()


@shared_task(name="clear_temp_directory")
def clear_temp_directory():
    if not settings.USE_AZURE:
        # disable if not in azure env
        logger.error('This task is for azure environment only')
        return
    logger.info('Starting cleaning temp directory on azure env.')
    export_data_dir = os.path.join(settings.MEDIA_ROOT, 'export_data')
    if os.path.exists(export_data_dir):
        shutil.rmtree(export_data_dir)
    tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp')
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    layer_files = os.path.join(settings.MEDIA_ROOT, 'layer_files')
    if os.path.exists(layer_files):
        shutil.rmtree(layer_files)
    error_reports = os.path.join(settings.MEDIA_ROOT, 'error_reports')
    if os.path.exists(error_reports):
        shutil.rmtree(error_reports)
    # create export data and tmp
    if not os.path.exists(export_data_dir):
        os.makedirs(export_data_dir)
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    logger.info('Finished cleaning temp directory on azure env.')
    calculate_temp_directory()


@shared_task(name="remove_old_exported_data")
def remove_old_exported_data():
    if settings.USE_AZURE:
        client = DirectoryClient(settings.AZURE_STORAGE,
                                 settings.AZURE_STORAGE_CONTAINER)
        export_data_dir = 'media/export_data'
        client.rmdir(export_data_dir)
    else:
        if os.path.exists(settings.EXPORT_FOLDER_OUTPUT):
            shutil.rmtree(settings.EXPORT_FOLDER_OUTPUT)
        if not os.path.exists(settings.EXPORT_FOLDER_OUTPUT):
            os.makedirs(settings.EXPORT_FOLDER_OUTPUT)
