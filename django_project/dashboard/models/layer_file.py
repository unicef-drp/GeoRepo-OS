from django.db import models
from django.conf import settings

GEOJSON = 'GEOJSON'
SHAPEFILE = 'SHAPEFILE'
GEOPACKAGE = 'GEOPACKAGE'


class LayerFile(models.Model):

    LAYER_TYPE_CHOICES = (
        (GEOJSON, GEOJSON),
        (SHAPEFILE, SHAPEFILE),
        (GEOPACKAGE, GEOPACKAGE)
    )

    id = models.AutoField(primary_key=True)

    meta_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    upload_date = models.DateTimeField(
        null=True,
        blank=True
    )

    layer_file = models.FileField(
        upload_to='layer_files/%Y/%m/%d/'
    )

    processed = models.BooleanField(
        default=False
    )

    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        default='',
        blank=True,
        max_length=512
    )

    level = models.CharField(
        default='',
        blank=True,
        max_length=128
    )

    entity_type = models.CharField(
        default='',
        blank=True,
        max_length=256
    )

    layer_upload_session = models.ForeignKey(
        'dashboard.LayerUploadSession',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    location_type_field = models.CharField(
        max_length=255,
        default='',
        blank=True
    )

    parent_id_field = models.CharField(
        max_length=255,
        default='',
        blank=True
    )

    source_field = models.CharField(
        max_length=255,
        default='',
        blank=True
    )

    id_fields = models.JSONField(
        default=[],
        blank=True
    )

    name_fields = models.JSONField(
        default=[],
        blank=True
    )

    feature_count = models.IntegerField(
        null=True,
        blank=True
    )

    layer_type = models.CharField(
        max_length=100,
        blank=True,
        default=GEOJSON,
        choices=LAYER_TYPE_CHOICES
    )

    boundary_type = models.CharField(
        max_length=255,
        default='',
        blank=True
    )

    privacy_level_field = models.CharField(
        max_length=255,
        default='',
        blank=True
    )

    privacy_level = models.CharField(
        max_length=255,
        default='',
        blank=True,
        help_text='user input privacy level'
    )

    def __str__(self):
        return self.name
