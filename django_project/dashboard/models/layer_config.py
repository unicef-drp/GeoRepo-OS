from django.db import models
from django.conf import settings


class LayerConfig(models.Model):
    id = models.AutoField(primary_key=True)

    name = models.CharField(
        default='',
        blank=False,
        null=False,
        max_length=255
    )

    level = models.CharField(
        default='',
        blank=True,
        max_length=128
    )

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
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

    entity_type = models.CharField(
        default='',
        blank=True,
        max_length=256
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

    class Meta:
        verbose_name_plural = 'Layer Configs'
        ordering = ['created_at']

    def __str__(self) -> str:
        return self.name
