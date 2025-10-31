import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site

from georepo.models import (
    ExportRequestBase,
    ExportRequest, GEOJSON_EXPORT_TYPE,
    KML_EXPORT_TYPE, TOPOJSON_EXPORT_TYPE,
    SHAPEFILE_EXPORT_TYPE, ExportRequestStatusText,
    GEOPACKAGE_EXPORT_TYPE, DatasetExportRequest
)
from georepo.models.base_task_request import ERROR, DONE
from georepo.utils.exporter_base import DatasetViewExporterBase
from georepo.utils.geojson import GeojsonDatasetExporter
from georepo.utils.shapefile import (
    ShapefileDatasetExporter
)
from georepo.utils.kml import (
    KmlDatasetExporter
)
from georepo.utils.topojson import (
    TopojsonDatasetExporter
)
from georepo.utils.gpkg_file import (
    GPKGDatasetExporter
)
from dashboard.models.notification import (
    Notification,
    NOTIF_TYPE_DATASET_VIEW_EXPORTER,
    NOTIF_TYPE_DATASET_EXPORTER
)


logger = logging.getLogger(__name__)


def try_clear_temp_resource_on_error(exporter: DatasetViewExporterBase):
    try:
        exporter.do_remove_temp_dir()
    except Exception:
        pass


def _run_exporter(request, exporter):
    """Run exporter for Dataset or DatasetView."""
    if exporter is None:
        request.errors = f'Unknown export format: {request.format}'
        request.status = ERROR
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.save(update_fields=['errors', 'status', 'status_text'])
        return
    try:
        exporter.init_exporter()
        exporter.run()
    except Exception as ex:
        logger.error('Failed Process Exporter!')
        logger.error(ex, exc_info=True)
        request.status = ERROR
        request.errors = str(ex)
        request.task_id = None
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.save(update_fields=[
            'status', 'errors', 'task_id', 'status_text']
        )
        try_clear_temp_resource_on_error(exporter)
    finally:
        request.refresh_from_db()
        is_success = True if request.status == DONE else ERROR
        if request.source == 'dashboard':
            # send notification via dashboard
            message = (
                'Your download request for '
                f'{request.name}'
                ' is ready! Click here to view!'
            ) if is_success else (
                'Your download request for '
                f'{request.name}'
                ' is finished with error! Click here to view!'
            )
            payload = {
                'request_id': request.id,
                'severity': 'success' if is_success else 'error',
            }
            if isinstance(request, ExportRequest):
                payload['view_id'] = request.resource_id
            else:
                payload['dataset_id'] = request.resource_id
            Notification.objects.create(
                type=(
                    NOTIF_TYPE_DATASET_VIEW_EXPORTER if
                    isinstance(request, ExportRequest) else
                    NOTIF_TYPE_DATASET_EXPORTER
                ),
                message=message,
                recipient=request.submitted_by,
                payload=payload
            )
        # send email notification with download link
        notify_requester_exporter_finished(request)


@shared_task(name="dataset_exporter")
def dataset_exporter(request_id):
    request = DatasetExportRequest.objects.get(id=request_id)
    exporter = None
    if request.format == GEOJSON_EXPORT_TYPE:
        exporter = GeojsonDatasetExporter(request)
    elif request.format == SHAPEFILE_EXPORT_TYPE:
        exporter = ShapefileDatasetExporter(request)
    elif request.format == KML_EXPORT_TYPE:
        exporter = KmlDatasetExporter(request)
    elif request.format == TOPOJSON_EXPORT_TYPE:
        exporter = TopojsonDatasetExporter(request)
    elif request.format == GEOPACKAGE_EXPORT_TYPE:
        exporter = GPKGDatasetExporter(request)

    _run_exporter(request, exporter)


def notify_requester_exporter_finished(request: ExportRequestBase):
    current_site = Site.objects.get_current()
    scheme = 'https://'
    domain = current_site.domain
    if not domain.endswith('/'):
        domain = domain + '/'
    error_link = (
        f'{scheme}{domain}view_edit?id={request.resource_id}&tab=5'
    ) if isinstance(request, ExportRequest) else (
        f'{scheme}{domain}admin_boundaries/dataset_entities?'
        f'id={request.resource_id}&tab=10'
    )
    context = {
        'is_success': request.status == DONE,
        'view_name': request.name,
        'request_from': request.requester_name,
        'expiry_download_link': (
            f'{settings.EXPORT_DATA_EXPIRY_IN_HOURS} hours'
        ),
        'download_link': request.download_link,
        'error_link': error_link,
    }
    subject = ''
    if request.status == DONE:
        subject = f'Your download for {request.name} is ready'
    else:
        subject = (
            f'Error! Your download for {request.name} '
            'is finished with errors'
        )
    try:
        message = render_to_string(
            'emails/notify_export_request.html',
            context
        )
        send_mail(
            subject,
            None,
            settings.DEFAULT_FROM_EMAIL,
            [request.submitted_by.email],
            html_message=message,
            fail_silently=False
        )
    except Exception as ex:
        logger.error('Failed Sending Email in Exporter!')
        logger.error(ex, exc_info=True)
