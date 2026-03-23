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


class StorageLog(models.Model):
    """Class that represents logs of storage/memory."""

    date_time = models.DateTimeField(
        auto_now_add=True
    )

    storage_log = models.TextField(
        null=True,
        blank=True
    )

    memory_log = models.TextField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f'{self.date_time}'


class LogFile(models.Model):
    """Class that represent log file."""

    path = models.CharField(max_length=500, unique=True)
    size = models.PositiveBigIntegerField()
    created_on = models.DateTimeField()

    def filename(self):
        """Extracts the filename from the path."""
        return self.path.split('/')[-1]

    def __str__(self):
        return self.filename()


class CleanupDirectoryLog(models.Model):
    """Class that represents logs of cleanup."""

    date_time = models.DateTimeField(
        auto_now_add=True
    )
    storage_path = models.TextField(
        help_text='The path of the storage that was cleaned up.'
    )
    usage_percentage = models.FloatField(
        null=True,
        blank=True
    )
    critical_threshold = models.FloatField(
        null=True,
        blank=True
    )
    deleted_files_count = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    freed_space_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True
    )
    deleted_files = models.JSONField(
        null=True,
        blank=True,
        default=list
    )

    class Meta:  # noqa: D106
        ordering = ["-date_time"]
