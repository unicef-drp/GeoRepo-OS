from django.db import models
from georepo.models.base_task_request import BaseTaskRequest


# export types
GEOJSON_EXPORT_TYPE = 'GEOJSON'
SHAPEFILE_EXPORT_TYPE = 'SHAPEFILE'
KML_EXPORT_TYPE = 'KML'
TOPOJSON_EXPORT_TYPE = 'TOPOJSON'


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
        default=dict
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

    def __str__(self):
        return str(self.uuid)
