from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from georepo.models.dataset_view import DatasetView


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
        try:
            return '{0} - {1}'.format(
                self.dataset_view.name,
                self.zoom_level
            )
        except DatasetView.DoesNotExist:
            return '{0} - {1}'.format(
                self.dataset_view_id,
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
        try:
            return '{0} - Admin Level {1}'.format(
                self.view_tiling_config,
                self.level
            )
        except DatasetViewTilingConfig.DoesNotExist:
            return '{0} - Admin Level {1}'.format(
                self.view_tiling_config_id,
                self.level
            )

    class Meta:
        indexes = [
                    models.Index(fields=['view_tiling_config',
                                         'level',
                                         'simplify_tolerance'])
                ]


@receiver(post_save, sender=DatasetViewTilingConfig)
def dataset_view_tiling_config_post_create(
    sender,
    instance: DatasetViewTilingConfig,
    created, *args, **kwargs
):
    if getattr(instance, 'skip_signal', False):
        return
    if created:
        dataset_view = DatasetView.objects.get(id=instance.dataset_view_id)
        dataset_view.set_out_of_sync(
            tiling_config=True,
            product=False,
            vector_tile=True
        )
