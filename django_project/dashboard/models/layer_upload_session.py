from django.db import models
from django.conf import settings

DONE = 'Done'
PENDING = 'Pending'
CANCELED = 'Canceled'
PROCESSING = 'Processing'
ERROR = 'Error'
VALIDATING = 'Validating'
REVIEWING = 'Reviewing'
# pre-processing for auto matching parent entities
# flow: step3 (PENDING) ->  step4 (PRE_PROCESSING) ->
#   step4 (PENDING)
PRE_PROCESSING = 'Pre-processing'


class LayerUploadSession(models.Model):
    STATUS_CHOICES = (
        (DONE, DONE),
        (VALIDATING, VALIDATING),
        (PENDING, PENDING),
        (CANCELED, CANCELED),
        (ERROR, ERROR),
        (PROCESSING, PROCESSING),
        (REVIEWING, REVIEWING),
        (PRE_PROCESSING, PRE_PROCESSING),
    )

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    modified_at = models.DateTimeField(
        auto_now=True
    )

    status = models.CharField(
        choices=STATUS_CHOICES,
        max_length=128,
        null=False,
        blank=False
    )

    message = models.TextField(
        null=True,
        blank=True
    )

    progress = models.TextField(
        null=True,
        blank=True
    )

    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
    )

    last_step = models.IntegerField(
        null=True,
        blank=True
    )

    auto_matched_parent_ready = models.BooleanField(
        default=None,
        null=True,
        blank=True
    )

    is_historical_upload = models.BooleanField(
        default=False,
        null=True,
        blank=True
    )

    historical_start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    historical_end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256,
        help_text='running task id'
    )

    tolerance = models.FloatField(
        null=True,
        blank=True,
        help_text='Tolerance for geometry checker'
    )

    overlaps_threshold = models.FloatField(
        null=True,
        blank=True,
        help_text='Check for overlaps smaller than (map units sqr.)'
    )

    gaps_threshold = models.FloatField(
        null=True,
        blank=True,
        help_text='Check for gaps smaller than (map units sqr.)'
    )

    def __str__(self):
        return f'{self.source} - {self.status}'

    def is_read_only(self):
        if not self.dataset.is_active:
            return True
        return self.status in (DONE, REVIEWING, CANCELED)

    def is_in_progress(self):
        from dashboard.models.entity_upload import (
            STARTED, PROCESSING as UPLOAD_PROCESSING
        )
        if self.status == PRE_PROCESSING:
            return True
        # check for any processing entity upload status
        ongoing_uploads = self.entityuploadstatus_set.filter(
            status__in=[STARTED, UPLOAD_PROCESSING]
        )
        return ongoing_uploads.exists()

    def has_any_result(self):
        # check whether some processing have been done
        if self.auto_matched_parent_ready:
            # result from Pre-processing
            return True
        # check result from qc_validation
        existing_uploads = self.entityuploadstatus_set.exclude(
            status=''
        )
        return existing_uploads.exists()

    @classmethod
    def get_upload_session_for_user(self, user):
        upload_sessions = LayerUploadSession.objects.filter(
            uploader=user
        ).order_by('-started_at')
        if user.is_superuser:
            upload_sessions = (
                LayerUploadSession.objects.filter(
                    dataset__isnull=False
                ).order_by('-started_at')
            )
        return upload_sessions
