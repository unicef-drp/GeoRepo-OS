from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from georepo.models.dataset import Dataset


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
        try:
            return '{0} - Admin Level {1}'.format(
                self.dataset_tiling_config,
                self.level
            )
        except DatasetTilingConfig.DoesNotExist:
            return '{0} - Admin Level {1}'.format(
                self.dataset_tiling_config_id,
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


@receiver(post_save, sender=DatasetTilingConfig)
def dataset_tiling_config_post_create(
    sender, instance: DatasetTilingConfig, created, *args, **kwargs
):
    dataset = Dataset.objects.get(id=instance.dataset)
    dataset.sync_status = dataset.DatasetViewSyncStatus.OUT_OF_SYNC
    dataset.save(update_fields=['sync_status'])

    for view in dataset.datasetview_set.all():
        view.sync_status = view.DatasetViewSyncStatus.OUT_OF_SYNC
        view.save(update_fields=['sync_status'])
