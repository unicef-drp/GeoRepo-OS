# coding=utf-8
"""
GeoRepo.

.. note:: Models for tracking Django management command executions
"""

from django.db import models

__all__ = ['CommandExecution']


class CommandExecution(models.Model):
    """Track execution of a Django management command run via celery."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]

    # Command details
    command_name = models.CharField(max_length=255, db_index=True)
    command_args = models.JSONField(default=list, blank=True)
    command_kwargs = models.JSONField(default=dict, blank=True)

    # Celery tracking
    celery_task_id = models.CharField(
        null=True, blank=True,
        max_length=255, db_index=True
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    # Output capture
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    triggered_by = models.CharField(max_length=255, blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:  # noqa: D106
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['command_name', '-created_at']),
        ]

    def __str__(self):
        """Return a readable representation of the execution."""
        if self.celery_task_id:
            return (
                f'{self.command_name} - {self.status} '
                f'({self.celery_task_id[:8]})'
            )
        return f'{self.command_name} - {self.status}'

    @property
    def duration(self):
        """Calculate execution duration in seconds.

        :return: Duration in seconds, or None if not yet completed.
        :rtype: float or None
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def duration_display(self):
        """Return a human-readable duration.

        :return: Duration formatted as seconds, minutes, or hours.
        :rtype: str
        """
        duration = self.duration
        if duration is None:
            return 'N/A'

        if duration < 60:
            return f'{duration:.2f}s'
        elif duration < 3600:
            return f'{duration / 60:.2f}m'
        else:
            return f'{duration / 3600:.2f}h'
