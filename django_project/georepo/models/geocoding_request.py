from django.db import models
import uuid
from django.conf import settings


# task statuses
PENDING = 'PENDING'
PROCESSING = 'PROCESSING'
DONE = 'DONE'
ERROR = 'ERROR'
CANCELLED = 'CANCELLED'

# uploaded file types
GEOJSON = 'GEOJSON'
SHAPEFILE = 'SHAPEFILE'
GEOPACKAGE = 'GEOPACKAGE'


class GeocodingRequest(models.Model):

    STATUS_CHOICES = (
        (PENDING, PENDING),
        (PROCESSING, PROCESSING),
        (DONE, DONE),
        (ERROR, ERROR),
        (CANCELLED, CANCELLED)
    )

    FILE_TYPE_CHOICES = (
        (GEOJSON, GEOJSON),
        (SHAPEFILE, SHAPEFILE),
        (GEOPACKAGE, GEOPACKAGE)
    )

    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICES,
        null=True,
        blank=True
    )

    task_id = models.CharField(
        max_length=256
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )

    submitted_on = models.DateTimeField()

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True
    )

    parameters = models.TextField(
        null=True,
        blank=True
    )

    errors = models.TextField(
        null=True,
        blank=True
    )

    progress = models.FloatField(
        null=True,
        blank=True
    )

    file = models.FileField(
        upload_to='layer_files/%Y/%m/%d/'
    )

    file_type = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        choices=FILE_TYPE_CHOICES,
        default=GEOJSON
    )

    output_file = models.FileField(
        upload_to='layer_files/%Y/%m/%d/'
    )

    feature_count = models.IntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return str(self.uuid)
