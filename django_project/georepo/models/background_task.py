from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class BackgroundTask(models.Model):
    class BackgroundTaskStatus(models.TextChoices):
        QUEUED = 'Queued', _('Queued')
        RUNNING = 'Running', _('Running')
        STOPPED = 'Stopped', _('Stopped')
        COMPLETED = 'Completed', _('Completed')
        CANCELLED = 'Cancelled', _('Cancelled')
        INVALIDATED = 'Invalidated', _('Invalidated')
    
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    description = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    last_update = models.DateTimeField(
        auto_now=True,
        editable=True
    )

    status = models.CharField(
        max_length=255,
        choices=BackgroundTaskStatus.choices,
        null=True,
        blank=True
    )

    task_id = models.CharField(
        max_length=256,
        unique=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True
    )

    parameters = models.TextField(
        null=True,
        blank=True
    )

    errors = models.TextField(
        null=True,
        blank=True
    )

    celery_retry = models.IntegerField(
        default=0
    )

    celery_last_retry_at = models.DateTimeField(
        null=True,
        blank=True
    )

    celery_retry_reason = models.TextField(
        null=True,
        blank=True
    )
