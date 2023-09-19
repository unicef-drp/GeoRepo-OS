import uuid
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from guardian.models import UserObjectPermissionBase
from guardian.models import GroupObjectPermissionBase


class Dataset(models.Model):
    class Meta:
        permissions = [
            ('view_dataset_level_1', 'Read - Level 1'),
            ('view_dataset_level_2', 'Read - Level 2'),
            ('view_dataset_level_3', 'Read - Level 3'),
            ('view_dataset_level_4', 'Read - Level 4'),
            ('upload_data', 'Upload Data'),
            ('upload_data_level_0', 'Upload Data Level 0'),
            ('review_upload', 'Review Upload'),
            ('edit_metadata_dataset', 'Edit Metadata Dataset'),
            ('invite_user_dataset', 'Invite User'),
            ('remove_user_dataset', 'Remove User'),
            ('archive_dataset', 'Archive Dataset'),
            ('dataset_add_view', 'Create View'),
        ]

    class DatasetTilingStatus(models.TextChoices):
        PENDING = 'PE', _('Pending')
        PROCESSING = 'PR', _('Processing')
        DONE = 'DO', _('Done')
        ERROR = 'ER', _('Error')

    class SyncStatus(models.TextChoices):
        OUT_OF_SYNC = 'out_of_sync', _('Out of Sync')
        SYNCING = 'syncing', _('Syncing')
        SYNCED = 'synced', _('Synced')

    label = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    description = models.TextField(
        default='',
        blank=True
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        blank=True
    )

    vector_tiles_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=''
    )

    last_update = models.DateTimeField(
        null=True,
        blank=True
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    module = models.ForeignKey(
        'georepo.Module',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
        default=timezone.now
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    styles = models.JSONField(
        null=True,
        blank=True,
        help_text='Styling in json'
    )

    style_source_name = models.CharField(
        blank=True,
        null=True,
        help_text='Source name in styles',
        max_length=256
    )

    geometry_similarity_threshold_new = models.FloatField(
        null=True,
        blank=True,
        default=0.9,
        help_text=(
            'Threshold of percentage of the new boundary area '
            'covered by the old matching boundary (% new). '
            'Value from 0-1'
        )
    )

    geometry_similarity_threshold_old = models.FloatField(
        null=True,
        blank=True,
        default=0.9,
        help_text=(
            'Threshold of percentage of the old boundary area '
            'covered by the new matching boundary (% old). '
            'Value from 0-1'
        )
    )

    tiling_status = models.CharField(
        max_length=2,
        choices=DatasetTilingStatus.choices,
        default=DatasetTilingStatus.PENDING
    )

    sync_status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.OUT_OF_SYNC
    )

    tiling_start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    tiling_end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    tiling_progress = models.FloatField(
        null=True,
        blank=True,
        default=0
    )

    simplification_task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    short_code = models.CharField(
        blank=True,
        default='',
        max_length=16
    )

    generate_adm0_default_views = models.BooleanField(
        null=True,
        blank=True,
        default=False
    )

    max_privacy_level = models.IntegerField(
        default=4
    )

    min_privacy_level = models.IntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True,
        help_text='To deprecate/activate dataset',
    )

    deprecated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    deprecated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deprecated_dataset'
    )

    simplification_progress = models.TextField(
        null=True,
        blank=True,
        default='Entity simplification finished'
    )

    is_simplified = models.BooleanField(
        default=False
    )

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()

        self.last_update = timezone.now()

        # Clear cache
        cache_keys = cache.get('cache_keys')
        if cache_keys:
            dataset_keys = cache_keys.get('Dataset', [])
            if dataset_keys:
                to_removed = []
                for dataset_key in dataset_keys:
                    if str(self.uuid) in dataset_key:
                        cache.delete(dataset_key)
                        to_removed.append(dataset_key)
                for remove in to_removed:
                    dataset_keys.remove(remove)
                cache_keys['Dataset'] = dataset_keys
                cache.set('cache_keys', cache_keys)

        try:
            dataset_caches = (
                cache._cache.get_client().keys(f'*{str(self.uuid)}*')
            )
            if dataset_caches:
                for dataset_cache in dataset_caches:
                    cache.delete(
                        str(dataset_cache).split(':')[-1].replace('\'', ''))
        except AttributeError:
            pass

        return super(Dataset, self).save(*args, **kwargs)

    def set_view_out_of_sync(
        self,
        tiling_config=False,
        vector_tile=False,
        product=False
    ):
        for view in self.datasetview_set.all():
            view.set_out_of_sync(
                tiling_config=tiling_config,
                vector_tile=vector_tile,
                product=product
            )

    def set_view_synced(
        self,
        tiling_config=False,
        vector_tile=False,
        product=False
    ):
        for view in self.datasetview_set.all():
            view.set_sync(
                tiling_config=tiling_config,
                vector_tile=vector_tile,
                product=product
            )

    def __str__(self):
        return self.label


class DatasetUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Dataset, on_delete=models.CASCADE)


class DatasetGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Dataset, on_delete=models.CASCADE)


@receiver(post_save, sender=Dataset)
def dataset_post_create(sender, instance: Dataset, created, *args, **kwargs):
    from georepo.utils.permission import (
        grant_dataset_owner
    )
    if created:
        grant_dataset_owner(instance)


@receiver(post_delete, sender=Dataset)
def dataset_post_delete(sender, instance: Dataset, *args, **kwargs):
    from core.celery import app

    if instance.task_id:
        app.control.revoke(instance.task_id, terminate=True, signal='SIGKILL')

    if instance.simplification_task_id:
        app.control.revoke(instance.simplification_task_id, terminate=True,
                           signal='SIGKILL')


class DatasetAdminLevelName(models.Model):

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    label = models.CharField(
        max_length=255,
        null=False,
        blank=True,
        default=''
    )

    level = models.IntegerField(
        default=0
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f'Level {self.level} - {self.label}'
