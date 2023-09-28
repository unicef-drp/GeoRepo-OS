from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class BackgroundTask(models.Model):
    class BackgroundTaskStatus(models.TextChoices):
        QUEUED = 'Queued', _('Queued')
        RUNNING = 'Running', _('Running')
        STOPPED = 'Stopped', _('Stopped with error')
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

    def is_possible_interrupted(self):
        if (
            self.status == BackgroundTask.BackgroundTaskStatus.QUEUED or
            self.status == BackgroundTask.BackgroundTaskStatus.RUNNING
        ):
            # check if last_update is more than 30mins than current date time
            if self.last_update:
                diff_seconds = timezone.now() - self.last_update
                return diff_seconds.total_seconds() >= 1800
        return False

    def __str__(self) -> str:
        return self.name
