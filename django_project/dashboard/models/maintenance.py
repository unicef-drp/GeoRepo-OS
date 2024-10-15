from django.db import models
from django.conf import settings
from django.utils import timezone


class Maintenance(models.Model):

    message = models.CharField(
        max_length=600,
        blank=False,
        null=False
    )

    scheduled_date = models.DateTimeField(
        null=True,
        blank=True
    )

    scheduled_from_date = models.DateTimeField(
        default=timezone.now,
        null=False,
        blank=False
    )

    scheduled_end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            'Maintenance scheduled at'
            f'{self.scheduled_from_date} - '
            f'{self.scheduled_end_date}'
        )
