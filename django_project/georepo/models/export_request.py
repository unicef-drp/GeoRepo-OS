from enum import Enum
from django.db import models
from georepo.models.base_task_request import BaseTaskRequest


# export types
GEOJSON_EXPORT_TYPE = 'GEOJSON'
SHAPEFILE_EXPORT_TYPE = 'SHAPEFILE'
KML_EXPORT_TYPE = 'KML'
TOPOJSON_EXPORT_TYPE = 'TOPOJSON'

AVAILABLE_EXPORT_FORMAT_TYPES = [
    GEOJSON_EXPORT_TYPE,
    SHAPEFILE_EXPORT_TYPE,
    KML_EXPORT_TYPE,
    TOPOJSON_EXPORT_TYPE
]


# Status text
class ExportRequestStatusText(str, Enum):
    WAITING = 'waiting'
    QUEUED = 'queued'
    RUNNING = 'running'
    PREPARING_GEOJSON = 'preparing_geojson'
    PREPARING_SHP = 'preparing_shp'
    PREPARING_TOPOJSON = 'preparing_topojson'
    PREPARING_KML = 'preparing_kml'
    CREATING_ZIP_ARCHIVE = 'creating_zip_archive'
    READY = 'ready'
    ABORTED = 'aborted'
    EXPIRED = 'expired'

    def __str__(self) -> str:
        return self.value


class ExportRequest(BaseTaskRequest):

    FORMAT_CHOICES = (
        (GEOJSON_EXPORT_TYPE, GEOJSON_EXPORT_TYPE),
        (SHAPEFILE_EXPORT_TYPE, SHAPEFILE_EXPORT_TYPE),
        (KML_EXPORT_TYPE, KML_EXPORT_TYPE),
        (TOPOJSON_EXPORT_TYPE, TOPOJSON_EXPORT_TYPE)
    )

    dataset_view = models.ForeignKey(
        'georepo.DatasetView',
        on_delete=models.CASCADE
    )

    format = models.CharField(
        max_length=255,
        choices=FORMAT_CHOICES,
    )

    is_simplified_entities = models.BooleanField(
        default=False
    )

    simplification_zoom_level = models.IntegerField(
        null=True,
        blank=True
    )

    status_text = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    filters = models.JSONField(
        default=dict,
        null=True,
        blank=True
    )

    download_link = models.TextField(
        null=True,
        blank=True
    )

    download_link_expired_on = models.DateTimeField(
        null=True,
        blank=True
    )

    output_file = models.FileField(
        upload_to='exporter/%Y/%m/%d/',
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='API or dashboard'
    )

    file_output_size = models.IntegerField(
        null=True,
        blank=True,
        default=0
    )

    def __str__(self):
        return str(self.uuid)
