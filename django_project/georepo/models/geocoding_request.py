from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from georepo.models.base_task_request import BaseTaskRequest


# uploaded file types
GEOJSON = 'GEOJSON'
SHAPEFILE = 'SHAPEFILE'
GEOPACKAGE = 'GEOPACKAGE'


class GeocodingRequest(BaseTaskRequest):

    FILE_TYPE_CHOICES = (
        (GEOJSON, GEOJSON),
        (SHAPEFILE, SHAPEFILE),
        (GEOPACKAGE, GEOPACKAGE)
    )

    file = models.FileField(
        upload_to='geocoding/%Y/%m/%d/'
    )

    file_type = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        choices=FILE_TYPE_CHOICES,
        default=GEOJSON
    )

    output_file = models.FileField(
        upload_to='geocoding/%Y/%m/%d/',
        null=True,
        blank=True
    )

    feature_count = models.IntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return str(self.uuid)

    def table_name(self, schema_name="temp"):
        return f"{schema_name}.\"{str(self.uuid)}\""


@receiver(pre_delete, sender=GeocodingRequest)
def geocoding_request_pre_delete(sender, instance, using, **kwargs):
    from georepo.tasks.geocoding import geocoding_request_on_delete
    geocoding_request_on_delete(instance)
