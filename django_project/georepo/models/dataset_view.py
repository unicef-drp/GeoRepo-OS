from uuid import uuid4
from django.core.cache import cache

from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.db import connection
from django.utils.translation import gettext_lazy as _
from guardian.models import UserObjectPermissionBase
from guardian.models import GroupObjectPermissionBase
from taggit.managers import TaggableManager
from georepo.models.tag import TaggedRecord

DATASET_VIEW_LATEST_TAG = 'latest'
DATASET_VIEW_ALL_VERSIONS_TAG = 'all_versions'
DATASET_VIEW_DATASET_TAG = 'dataset'
DATASET_VIEW_SUBSET_TAG = 'subset'


class DatasetView(models.Model):
    class Meta:
        permissions = [
            ('edit_metadata_dataset_view', 'Edit metadata view'),
            ('edit_query_dataset_view', 'Edit SQL query'),
            ('ext_view_datasetview_level_1', 'Read View - Level 1'),
            ('ext_view_datasetview_level_2', 'Read View - Level 2'),
            ('ext_view_datasetview_level_3', 'Read View - Level 3'),
            ('ext_view_datasetview_level_4', 'Read View - Level 4'),
        ]

    class SyncStatus(models.TextChoices):
        OUT_OF_SYNC = 'out_of_sync', _('Out of Sync')
        SYNCING = 'syncing', _('Syncing')
        SYNCED = 'synced', _('Synced')

    class DatasetViewStatus(models.TextChoices):
        PENDING = 'PE', _('Pending')
        PROCESSING = 'PR', _('Processing')
        DONE = 'DO', _('Done')
        ERROR = 'ER', _('Error')

    class DefaultViewType(models.TextChoices):
        IS_LATEST = 'LATEST', _('Is Latest')
        ALL_VERSIONS = 'ALL', _('All Versions')

    tags = TaggableManager(
        blank=True,
        through=TaggedRecord
    )

    uuid = models.UUIDField(
        default=uuid4,
        help_text='UUID'
    )

    name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=True,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=True
    )

    last_update = models.DateTimeField(
        auto_now=True,
        editable=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    is_static = models.BooleanField(
        default=None,
        null=True,
        blank=True
    )

    query_string = models.TextField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=2,
        choices=DatasetViewStatus.choices,
        default=DatasetViewStatus.PENDING
    )

    is_tiling_config_match = models.BooleanField(
        default=True
    )

    vector_tile_sync_status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.OUT_OF_SYNC
    )

    product_sync_status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.OUT_OF_SYNC
    )

    bbox = models.CharField(
        max_length=100,
        default='',
        null=True,
        blank=True
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    default_type = models.CharField(
        max_length=256,
        choices=DefaultViewType.choices,
        null=True,
        blank=True,
        help_text='If not null, then this is default view'
    )

    default_ancestor_code = models.CharField(
        null=True,
        blank=True,
        max_length=256,
        help_text='If not null, then default view is per adm level 0'
    )

    tiles_updated_at = models.DateTimeField(
        auto_now_add=True,
        editable=True
    )

    max_privacy_level = models.IntegerField(
        default=4,
        help_text='updated when view is refreshed'
    )

    min_privacy_level = models.IntegerField(
        default=4,
        help_text='updated when view is refreshed'
    )

    simplification_task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    simplification_progress = models.TextField(
        null=True,
        blank=True
    )

    def get_resource_level_for_user(self, user_privacy_level):
        """
        Return allowed resource based on user level
        Example:
        - user_privacy_level=4, max=3, min=1, then result=3
        - user_privacy_level=2, max=3, min=1, then result=2
        """
        if user_privacy_level < self.min_privacy_level:
            raise ValueError('Invalid permission accessing view!')
        resource_level = (
            self.max_privacy_level if
            self.max_privacy_level <= user_privacy_level else
            user_privacy_level
        )
        return resource_level

    def set_out_of_sync(
        self,
        tiling_config=False,
        vector_tile=False,
        product=False
    ):
        update_fields = []
        if tiling_config:
            self.is_tiling_config_match = False
            update_fields.append('is_tiling_config_match')
        if vector_tile:
            self.vector_tile_sync_status = self.SyncStatus.OUT_OF_SYNC
            update_fields.append('vector_tile_sync_status')
        if product:
            self.product_sync_status = self.SyncStatus.OUT_OF_SYNC
            update_fields.append('product_sync_status')
        self.save(update_fields=update_fields)

    def set_synced(
        self,
        tiling_config=False,
        vector_tile=False,
        product=False
    ):
        update_fields = []
        if tiling_config:
            self.is_tiling_config_match = True
            update_fields.append('is_tiling_config_match')
        if vector_tile:
            self.vector_tile_sync_status = self.SyncStatus.SYNCED
            update_fields.append('vector_tile_sync_status')
        if product:
            self.product_sync_status = self.SyncStatus.SYNCED
            update_fields.append('product_sync_status')
        self.save(update_fields=update_fields)

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid4()

        # Clear cache
        cache_keys = cache.get('cache_keys')
        if cache_keys:
            dataset_keys = cache_keys.get('DatasetView', [])
            if dataset_keys:
                to_removed = []
                for dataset_key in dataset_keys:
                    if str(self.uuid) in dataset_key:
                        cache.delete(dataset_key)
                        to_removed.append(dataset_key)
                for remove in to_removed:
                    dataset_keys.remove(remove)
                cache_keys['DatasetView'] = dataset_keys
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

        for resource in self.datasetviewresource_set.all():
            resource.clear_permission_cache()

        return super(DatasetView, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @classmethod
    def get_fields(cls):
        return cls._meta.fields


class DatasetViewUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(DatasetView, on_delete=models.CASCADE)


class DatasetViewGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(DatasetView, on_delete=models.CASCADE)


@receiver(post_save, sender=DatasetView)
def view_post_create(sender, instance: DatasetView, created, *args, **kwargs):
    from georepo.utils.permission import (
        grant_datasetview_owner,
        MIN_PRIVACY_LEVEL,
        MAX_PRIVACY_LEVEL,
        grant_datasetview_manager,
        get_view_permission_privacy_level,
        grant_datasetview_viewer
    )
    from guardian.shortcuts import (
        get_users_with_perms,
        get_groups_with_perms
    )
    from guardian.core import ObjectPermissionChecker
    if not created:
        return

    # create resources per privacy level
    for i in range(MIN_PRIVACY_LEVEL, MAX_PRIVACY_LEVEL + 1):
        DatasetViewResource.objects.create(
            dataset_view=instance,
            privacy_level=i
        )
    actors = []
    owner = instance.created_by
    if owner is None:
        owner = instance.dataset.created_by
    grant_datasetview_owner(instance, owner)
    actors.append(owner.id)
    dataset = instance.dataset
    if owner.id != dataset.created_by.id:
        # grant to dataset owner
        grant_datasetview_owner(instance, dataset.created_by)
        actors.append(dataset.created_by.id)
    dataset_groups = get_groups_with_perms(dataset)
    for group in dataset_groups:
        checker = ObjectPermissionChecker(group)
        # test if group can add view -> manager
        if (
            checker.has_perm('dataset_add_view', dataset) or
            checker.has_perm('upload_data', dataset)
        ):
            grant_datasetview_manager(instance, group)
        # test if viewer
        privacy_level = get_view_permission_privacy_level(checker, dataset)
        if privacy_level > 0:
            grant_datasetview_viewer(instance, group)
    # grant viewer of datasets to users
    viewers = get_users_with_perms(
        dataset,
        with_group_users=False
    ).exclude(
        id__in=actors
    )
    for viewer in viewers:
        privacy_level = get_view_permission_privacy_level(viewer, dataset)
        if (
            viewer.has_perm('upload_data', dataset) or
            viewer.has_perm('dataset_add_view', dataset)
        ):
            # grant manager to usr
            grant_datasetview_manager(instance, viewer)
        elif privacy_level > 0:
            grant_datasetview_viewer(instance, viewer)


@receiver(post_delete, sender=DatasetView)
def view_post_delete(sender, instance: DatasetView, *args, **kwargs):
    from core.celery import app

    if instance.task_id:
        app.control.revoke(
            instance.task_id,
            terminate=True,
            signal='SIGKILL'
        )
    if instance.simplification_task_id:
        app.control.revoke(
            instance.simplification_task_id,
            terminate=True,
            signal='SIGKILL'
        )
    view_name = instance.uuid
    if instance.is_static:
        sql = (
            'DROP MATERIALIZED VIEW IF EXISTS "{view_name}"'.format(
                view_name=view_name,
            )
        )
    else:
        sql = (
            'DROP VIEW IF EXISTS "{view_name}"'.format(
                view_name=view_name,
            )
        )
    cursor = connection.cursor()
    cursor.execute('''%s''' % sql)


class DatasetViewResource(models.Model):
    """
    Resource of view for each privacy level
    """

    class SyncStatus(models.TextChoices):
        OUT_OF_SYNC = 'out_of_sync', _('Out of Sync')
        SYNCING = 'syncing', _('Syncing')
        SYNCED = 'synced', _('Synced')

    dataset_view = models.ForeignKey(
        'georepo.DatasetView',
        null=True,
        on_delete=models.CASCADE
    )

    privacy_level = models.IntegerField(
        default=4
    )

    uuid = models.UUIDField(
        default=uuid4,
        help_text='UUID'
    )

    product_sync_status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.OUT_OF_SYNC
    )

    vector_tile_sync_status = models.CharField(
        max_length=15,
        choices=SyncStatus.choices,
        default=SyncStatus.OUT_OF_SYNC
    )

    status = models.CharField(
        max_length=2,
        choices=DatasetView.DatasetViewStatus.choices,
        default=DatasetView.DatasetViewStatus.PENDING
    )

    vector_tiles_task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    data_product_task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    vector_tiles_updated_at = models.DateTimeField(
        auto_now_add=True,
        editable=True
    )

    vector_tiles_progress = models.FloatField(
        null=True,
        blank=True,
        default=0
    )

    data_product_progress = models.FloatField(
        null=True,
        blank=True,
        default=0
    )

    vector_tiles_log = models.TextField(
        default='',
        blank=True
    )

    bbox = models.CharField(
        max_length=100,
        default='',
        null=True,
        blank=True
    )

    vector_tiles_size = models.FloatField(
        default=0
    )

    entity_count = models.IntegerField(
        default=0
    )

    @property
    def resource_id(self):
        return str(self.uuid)

    @property
    def vector_tiles_exist(self):
        return self.vector_tiles_size > 0

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_view_resource',
                fields=['dataset_view', 'privacy_level']
            )
        ]

    def clear_permission_cache(self, token=None):
        try:
            key = str(self.uuid)
            if token:
                key = f'{str(self.uuid)}{token}'
            dataset_caches = (
                cache._cache.get_client().keys(f'*{key}*')
            )
            if dataset_caches:
                for dataset_cache in dataset_caches:
                    cache.delete(
                        str(dataset_cache).split(':')[-1].replace(
                            '\'',
                            ''
                        )
                    )
        except AttributeError:
            pass


class DatasetViewResourceLog(models.Model):
    dataset_view_resource = models.ForeignKey(
        DatasetViewResource,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )
    logs = models.JSONField(
        help_text='Logs of upload',
        default=dict,
        null=True,
        blank=True
    )

    def add_log(self, log_text, exec_time):
        if log_text in self.logs:
            self.logs[log_text] = {
                'count': self.logs[log_text]['count'] + 1,
                'avg_time': (self.logs[log_text]['avg_time'] + exec_time) / 2,
                'total_time': self.logs[log_text]['avg_time'] + exec_time
            }
        else:
            self.logs[log_text] = {
                'count': 1,
                'avg_time': exec_time,
                'total_time': exec_time
            }
        self.save(update_fields=['logs'])


@receiver(post_delete, sender=DatasetViewResource)
def view_res_post_delete(sender, instance: DatasetViewResource,
                         *args, **kwargs):
    from dashboard.tasks.export import remove_view_resource_data
    from core.celery import app

    if instance.vector_tiles_task_id:
        app.control.revoke(
            instance.vector_tiles_task_id,
            terminate=True,
            signal='SIGKILL'
        )
    remove_view_resource_data.delay(str(instance.uuid))


@receiver(post_save, sender=DatasetViewResource)
def view_res_post_save(sender, instance: DatasetViewResource,
                       *args, **kwargs):
    from georepo.utils.dataset_view import (
        get_view_tiling_status,
        get_view_product_status
    )
    # update dataset view status
    view: DatasetView = instance.dataset_view
    view_res_qs = DatasetViewResource.objects.filter(
        dataset_view=view,
        entity_count__gte=0
    )
    tiling_status, _ = get_view_tiling_status(view_res_qs)
    product_status, _ = get_view_product_status(view_res_qs)

    tiling_status_mapping = {
        'Pending': DatasetView.DatasetViewStatus.PENDING,
        'Error': DatasetView.DatasetViewStatus.PENDING,
        'Processing': DatasetView.DatasetViewStatus.PENDING,
        'Done': DatasetView.DatasetViewStatus.PENDING,
    }

    sync_status_mapping = {
        'Pending': DatasetView.SyncStatus.OUT_OF_SYNC,
        'Error': DatasetView.SyncStatus.OUT_OF_SYNC,
        'Processing': DatasetView.SyncStatus.SYNCING,
        'Done': DatasetView.SyncStatus.SYNCED,
    }

    if tiling_status != 'Ready':
        view.status = tiling_status_mapping[tiling_status]
        view.vector_tile_sync_status = sync_status_mapping[tiling_status]
    if product_status != 'Ready':
        view.product_sync_status = sync_status_mapping[product_status]

    view.save(
        update_fields=[
            'status',
            'vector_tile_sync_status',
            'product_sync_status'
        ]
    )


@receiver(pre_save, sender=DatasetView)
def dataset_view_pre_save(
    sender,
    instance: DatasetView,
    update_fields=None,
    **kwargs
):
    try:
        old_instance = DatasetView.objects.get(id=instance.id)
        if (
            old_instance.query_string != instance.query_string and
            old_instance.vector_tile_sync_status != (
                DatasetView.SyncStatus.OUT_OF_SYNC
            ) and
            old_instance.product_sync_status != (
                DatasetView.SyncStatus.OUT_OF_SYNC
            )
        ):
            instance.set_out_of_sync(
                tiling_config=False
            )
    except DatasetView.DoesNotExist:
        return None
