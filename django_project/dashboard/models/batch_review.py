from django.db import models
from django.conf import settings

PENDING = 'Pending'
PROCESSING = 'Processing'
ERROR = 'Error'
DONE = 'Done'


class BatchReview(models.Model):

    STATUS_CHOICES = (
        (PENDING, PENDING),
        (PROCESSING, PROCESSING),
        (ERROR, ERROR),
        (DONE, DONE),
    )

    review_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
    )

    is_approve = models.BooleanField(
        null=False,
        blank=False
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    started_at = models.DateTimeField(
        editable=True,
        null=True,
        blank=True
    )

    finished_at = models.DateTimeField(
        editable=True,
        null=True,
        blank=True
    )

    logs = models.TextField(
        null=True,
        blank=True
    )

    upload_ids = models.JSONField(
        help_text='List of entity uploads',
        default=list,
        null=True,
        blank=True
    )

    processed_ids = models.JSONField(
        help_text='List of entity uploads that has been processed',
        default=list,
        null=True,
        blank=True
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

    status = models.CharField(
        max_length=100,
        blank=True,
        default='',
        choices=STATUS_CHOICES
    )
