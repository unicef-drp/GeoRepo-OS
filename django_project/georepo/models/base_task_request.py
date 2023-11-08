from django.db import models
import uuid
from django.conf import settings


# task statuses
PENDING = 'PENDING'
PROCESSING = 'PROCESSING'
DONE = 'DONE'
ERROR = 'ERROR'
CANCELLED = 'CANCELLED'

class BaseTaskRequest(models.Model):

    STATUS_CHOICES = (
        (PENDING, PENDING),
        (PROCESSING, PROCESSING),
        (DONE, DONE),
        (ERROR, ERROR),
        (CANCELLED, CANCELLED)
    )

    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICES,
        null=True,
        blank=True
    )

    task_id = models.CharField(
        max_length=256,
        null=True,
        blank=True
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )

    submitted_on = models.DateTimeField()

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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

    progress = models.FloatField(
        null=True,
        blank=True
    )

    last_min_poll_count = models.IntegerField(
        default=0
    )

    last_min_poll_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        """Meta class for abstract base task request."""
        abstract = True

    def __str__(self):
        return str(self.uuid)

