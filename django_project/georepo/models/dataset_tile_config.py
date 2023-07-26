from django.db import models
from django.utils import timezone


class DatasetTilingConfig(models.Model):

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    zoom_level = models.IntegerField(
        null=False,
        blank=False,
        default=0
    )

    def __str__(self):
        return '{0} - {1}'.format(
            self.dataset.label,
            self.zoom_level
        )

    class Meta:
        ordering = [
            'dataset__label',
            'zoom_level'
        ]


class AdminLevelTilingConfig(models.Model):

    dataset_tiling_config = models.ForeignKey(
        'georepo.DatasetTilingConfig',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    level = models.IntegerField(
        default=0
    )

    simplify_tolerance = models.FloatField(
        default=0
    )

    def __str__(self):
        return '{0} - Admin Level {1}'.format(
            self.dataset_tiling_config,
            self.level
        )


class TemporaryTilingConfig(models.Model):
    """Tiling config temporary for generating preview."""

    session = models.CharField(
        max_length=256
    )

    zoom_level = models.IntegerField(
        null=False,
        blank=False,
        default=0
    )

    level = models.IntegerField(
        default=0
    )

    simplify_tolerance = models.FloatField(
        default=0
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
        default=timezone.now
    )
