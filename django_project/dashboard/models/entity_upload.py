from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

PROCESSING = 'Processing'
VALID = 'Valid'
ERROR = 'Error'
STARTED = 'Started'
REVIEWING = 'Reviewing'
APPROVED = 'Approved'
REJECTED = 'Rejected'
PROCESSING_APPROVAL = 'Processing_Approval'


class EntityUploadStatus(models.Model):

    STATUS_CHOICES = (
        (STARTED, STARTED),
        (VALID, VALID),
        (ERROR, ERROR),
        (PROCESSING, PROCESSING),
        (REVIEWING, REVIEWING),
        (APPROVED, APPROVED),
        (REJECTED, REJECTED),
        (PROCESSING_APPROVAL, PROCESSING_APPROVAL),
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

    started_at = models.DateTimeField(
        auto_now_add=True
    )

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
        default={},
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
