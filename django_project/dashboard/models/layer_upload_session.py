import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

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

UPLOAD_PROCESS_PREPARE_VALIDATION = 'Preparing for Validation'
UPLOAD_PROCESS_COUNTRIES_SELECTION = (
    'Processing Countries Selection'
)
UPLOAD_PROCESS_COUNTRIES_VALIDATION = 'Countries Validation'
UPLOAD_PROCESS_IMPORT_FOR_REVIEW = 'Processing selected countries for review'
UPLOAD_PROCESS_PREPARE_FOR_REVIEW = 'Preparing for Review'


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

    UPLOAD_PROCESSING_CHOICES = (
        (UPLOAD_PROCESS_PREPARE_VALIDATION,
         UPLOAD_PROCESS_PREPARE_VALIDATION),
        (UPLOAD_PROCESS_COUNTRIES_SELECTION,
         UPLOAD_PROCESS_COUNTRIES_SELECTION),
        (UPLOAD_PROCESS_COUNTRIES_VALIDATION,
         UPLOAD_PROCESS_COUNTRIES_VALIDATION),
        (UPLOAD_PROCESS_IMPORT_FOR_REVIEW,
         UPLOAD_PROCESS_IMPORT_FOR_REVIEW),
        (UPLOAD_PROCESS_PREPARE_FOR_REVIEW,
         UPLOAD_PROCESS_PREPARE_FOR_REVIEW),
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
        default='',
        db_index=True
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

    current_process = models.CharField(
        choices=UPLOAD_PROCESSING_CHOICES,
        max_length=128,
        null=True,
        blank=True
    )

    current_process_uuid = models.CharField(
        max_length=255,
        default='',
        blank=True,
        null=True
    )

    validation_summaries = models.JSONField(
        help_text='Pre-validation summary',
        default=dict
    )

    validation_report = models.FileField(
        upload_to='upload_session_reports',
        null=True
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
        if self.status == PRE_PROCESSING or self.status == PROCESSING:
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

    def session_state(self):
        return {
            'is_read_only': self.is_read_only(),
            'is_in_progress': self.is_in_progress(),
            'has_any_result': self.has_any_result()
        }

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


class LayerUploadSessionMetadata(models.Model):
    """Store metadata in json for upload session."""

    session = models.OneToOneField(
        LayerUploadSession,
        on_delete=models.CASCADE
    )

    adm0_default_codes = models.JSONField(
        default=list,
        blank=True,
        null=True
    )

    total_adm0 = models.IntegerField(
        default=0,
        blank=True,
        null=True
    )


class LayerUploadSessionActionLog(models.Model):

    STATUS_CHOICES = (
        (DONE, DONE),
        (PENDING, PENDING),
        (ERROR, ERROR),
        (PROCESSING, PROCESSING),
    )

    session = models.ForeignKey(
        LayerUploadSession,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=255,
        default='',
        blank=True,
        null=True
    )

    status = models.CharField(
        choices=STATUS_CHOICES,
        max_length=128,
        null=False,
        blank=False,
        default=PENDING
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True
    )

    data = models.JSONField(
        default=dict,
        blank=True,
        null=True
    )

    task_id = models.CharField(
        blank=True,
        default='',
        max_length=256,
        help_text='running task id'
    )

    uuid = models.UUIDField(
        default=uuid.uuid4
    )

    progress = models.FloatField(
        null=True,
        blank=True,
        default=0
    )

    result = models.JSONField(
        default=dict,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.action

    def on_started(self):
        self.started_at = timezone.now()
        self.status = PROCESSING
        self.progress = 0
        self.result = {}
        self.save(update_fields=['started_at', 'status',
                                 'progress', 'result'])

    def on_finished(self, is_success, result):
        self.finished_at = timezone.now()
        self.status = DONE if is_success else ERROR
        self.progress = 100
        self.result = result
        self.save(update_fields=['finished_at', 'status',
                                 'progress', 'result'])
        # remove ref from session
        self.session.current_process = None
        self.session.current_process_uuid = None
        self.session.save(update_fields=['current_process',
                                         'current_process_uuid'])
