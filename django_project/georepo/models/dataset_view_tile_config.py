from django.db import models


class DatasetViewTilingConfig(models.Model):

    dataset_view = models.ForeignKey(
        'georepo.DatasetView',
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
            self.dataset_view.name,
            self.zoom_level
        )

    class Meta:
        ordering = [
            'dataset_view__id',
            'zoom_level'
        ]


class ViewAdminLevelTilingConfig(models.Model):

    view_tiling_config = models.ForeignKey(
        'georepo.DatasetViewTilingConfig',
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
