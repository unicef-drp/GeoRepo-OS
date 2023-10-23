import logging
from django.db import models
from django.contrib.gis.db import models as GisModels
from django.db.models.signals import pre_delete
from django.utils import timezone
from django.dispatch import receiver
from georepo.models.dataset import Dataset
from georepo.utils.permission import get_dataset_to_review
from dashboard.models.layer_upload_session import LayerUploadSession


logger = logging.getLogger(__name__)


PROCESSING = 'Processing'
VALID = 'Valid'
ERROR = 'Error'
WARNING = 'Warning'
STARTED = 'Started'
REVIEWING = 'Reviewing'
APPROVED = 'Approved'
REJECTED = 'Rejected'
PROCESSING_APPROVAL = 'Processing_Approval'
PROCESSING_ERROR = 'Stopped with Error'

IMPORTABLE_UPLOAD_STATUS_LIST = [VALID, WARNING]


class EntityUploadStatus(models.Model):

    STATUS_CHOICES = (
        (STARTED, STARTED),
        (VALID, VALID),
        (WARNING, WARNING),
        (ERROR, ERROR),
        (PROCESSING, PROCESSING),
        (REVIEWING, REVIEWING),
        (APPROVED, APPROVED),
        (REJECTED, REJECTED),
        (PROCESSING_APPROVAL, PROCESSING_APPROVAL),
        (PROCESSING_ERROR, PROCESSING_ERROR),
    )

    upload_session = models.ForeignKey(
        'dashboard.LayerUploadSession',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    original_geographical_entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        related_name='original_geographical_entity',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    revised_geographical_entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        related_name='revised_geographical_entity',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    revised_entity_id = models.CharField(
        max_length=100,
        default='',
        blank=True
    )

    revised_entity_name = models.CharField(
        max_length=300,
        default='',
        blank=True
    )

    status = models.CharField(
        max_length=100,
        blank=True,
        default='',
        choices=STATUS_CHOICES
    )

    logs = models.TextField(
        null=True,
        blank=True
    )

    summaries = models.JSONField(
        help_text='Validation summary',
        max_length=1024,
        null=True,
        blank=True
    )

    error_report = models.FileField(
        upload_to='error_reports',
        null=True
    )

    started_at = models.DateTimeField(default=timezone.now)

    comparison_data_ready = models.BooleanField(
        default=None,
        null=True,
        blank=True
    )

    boundary_comparison_summary = models.JSONField(
        null=True,
        blank=True
    )

    max_level = models.CharField(
        default='',
        null=True,
        blank=True,
        max_length=128,
        help_text='Selected max level to be imported'
    )

    max_level_in_layer = models.CharField(
        default='',
        null=True,
        blank=True,
        max_length=128,
        help_text='Max level for a country in layer file'
    )

    admin_level_names = models.JSONField(
        help_text='Name of admin levels',
        default=dict,
        null=True,
        blank=True
    )

    revision_number = models.IntegerField(
        null=True,
        blank=True
    )

    unique_code_version = models.FloatField(
        null=True,
        blank=True,
        help_text='All entities will have same version'
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256,
        help_text='running task id'
    )

    progress = models.TextField(
        null=True,
        blank=True
    )

    @property
    def comparison_running(self):
        return self.comparison_data_ready is not None

    def __str__(self):
        return f'{self.original_geographical_entity} - {self.status}'

    def get_entity_admin_level_name(self, level: int) -> str | None:
        """Return admin level name for entity at given level"""
        adm_level_name = None
        level_str = str(level)
        if (
            self.admin_level_names and
            level_str in self.admin_level_names
        ):
            adm_level_name = self.admin_level_names[level_str]
        return adm_level_name

    @classmethod
    def get_user_entity_upload_status(cls, user):
        datasets = Dataset.objects.all().order_by('created_at')
        datasets = get_dataset_to_review(
            user,
            datasets
        )
        entity_uploads = cls.objects.filter(
            status__in=[REVIEWING, APPROVED],
            upload_session__dataset__in=datasets
        ).order_by('-started_at')
        if not user.is_superuser:
            entity_uploads = entity_uploads.exclude(
                upload_session__uploader=user
            )
        return entity_uploads


@receiver(pre_delete, sender=EntityUploadStatus)
def delete_entity_upload(sender, instance, **kwargs):
    if instance.revised_geographical_entity:
        if not instance.revised_geographical_entity.is_approved:
            from georepo.models import GeographicalEntity
            GeographicalEntity.objects.filter(
                layer_file__in=instance.upload_session.layerfile_set.all()
            ).delete()


class EntityUploadChildLv1(models.Model):
    """
    In the upload that starts with level 1, system will generate
    automatically parent matching between this child entity to
    EntityUploadStatus.original_geographical_entity or
    EntityUploadStatus.revised_entity_id
    """

    entity_upload = models.ForeignKey(
        'dashboard.EntityUploadStatus',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    entity_id = models.CharField(
        max_length=100,
        blank=False,
        null=False
    )

    entity_name = models.CharField(
        max_length=300,
        blank=False,
        null=False
    )

    parent_entity_id = models.CharField(
        max_length=100,
        blank=False,
        null=False
    )

    is_parent_rematched = models.BooleanField(
        default=False,
        help_text='True if rematched parent has different default code'
    )

    feature_index = models.IntegerField(
        default=-1,
        blank=False,
        null=False,
        help_text='Index in layer file'
    )

    overlap_percentage = models.FloatField(
        default=0,
        null=True,
        blank=True
    )


class EntityUploadStatusLog(models.Model):
    layer_upload_session = models.ForeignKey(
        LayerUploadSession,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    entity_upload_status = models.ForeignKey(
        EntityUploadStatus,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    logs = models.JSONField(
        help_text='Logs of upload',
        default=dict,
        null=True,
        blank=True
    )
    parent_log = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return "Session: {0} - Upload Status: {1}".format(
            self.layer_upload_session,
            self.entity_upload_status
        )

    def add_log(self, log_text, exec_time):
        try:
            self.refresh_from_db()
            if log_text in self.logs:
                self.logs[log_text] = {
                    'count': self.logs[log_text]['count'] + 1,
                    'avg_time': (
                        self.logs[log_text]['avg_time'] + exec_time) / 2,
                    'total_time': self.logs[log_text]['avg_time'] + exec_time
                }
            else:
                self.logs[log_text] = {
                    'count': 1,
                    'avg_time': exec_time,
                    'total_time': exec_time
                }
            self.save(update_fields=['logs'])
        except self.DoesNotExist as ex:
            logger.error(f'Failed adding log {log_text}')
            logger.error(ex)

    def save(self, **kwargs):
        if self.entity_upload_status and not self.layer_upload_session:
            self.layer_upload_session = (
                self.entity_upload_status.upload_session
            )
        if self.entity_upload_status and not self.parent_log:
            self.parent_log = EntityUploadStatusLog.objects.filter(
                layer_upload_session=self.entity_upload_status.upload_session,
                entity_upload_status__isnull=True
            ).first()
        super().save(**kwargs)


class EntityTemp(GisModels.Model):

    upload_session = GisModels.ForeignKey(
        'dashboard.LayerUploadSession',
        on_delete=GisModels.CASCADE
    )

    layer_file = GisModels.ForeignKey(
        'dashboard.LayerFile',
        on_delete=GisModels.CASCADE
    )

    feature_index = GisModels.IntegerField(
        default=-1
    )

    level = GisModels.IntegerField(
        default=0
    )

    geometry = GisModels.GeometryField(
        null=True
    )

    entity_name = GisModels.CharField(
        max_length=255
    )

    entity_id = GisModels.CharField(
        max_length=100
    )

    parent_entity_id = GisModels.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    ancestor_entity_id = GisModels.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    is_parent_rematched = models.BooleanField(
        default=False,
        help_text='True if rematched parent has different default code'
    )

    overlap_percentage = models.FloatField(
        default=0,
        null=True,
        blank=True
    )

    def __str__(self) -> str:
        return self.entity_name + ' ' + self.entity_id

    class Meta:
        indexes = [
                    models.Index(fields=['level', 'entity_id']),
                    models.Index(fields=['level', 'ancestor_entity_id']),
                ]
