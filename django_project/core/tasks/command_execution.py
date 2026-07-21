# coding=utf-8
"""
GeoRepo.

.. note:: Task to execute a Django management command via celery
"""

import logging
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from core.celery import app
from core.models import CommandExecution

logger = logging.getLogger(__name__)

__all__ = ['execute_django_command']


@app.task(
    name='execute_django_command',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def execute_django_command(self, execution_id):
    """Execute a Django management command and track it in the database.

    :param self: reference to the current task instance
        (automatically passed by Celery)
    :type self: celery.app.task.Task
    :param execution_id: CommandExecution model instance ID
    :type execution_id: int
    """
    try:
        execution = CommandExecution.objects.get(id=execution_id)
    except CommandExecution.DoesNotExist:
        logger.error(f'CommandExecution {execution_id} not found')
        return

    # Update status to running
    execution.status = 'running'
    execution.started_at = timezone.now()
    execution.celery_task_id = self.request.id
    execution.save(update_fields=['status', 'started_at', 'celery_task_id'])

    # Prepare output capture
    stdout_capture = StringIO()
    stderr_capture = StringIO()

    try:
        # Execute the command
        call_command(
            execution.command_name,
            *execution.command_args,
            stdout=stdout_capture,
            stderr=stderr_capture,
            **execution.command_kwargs,
        )

        # Success - update record
        execution.status = 'success'
        execution.stdout = stdout_capture.getvalue()
        execution.stderr = stderr_capture.getvalue()
        execution.completed_at = timezone.now()
        execution.save(
            update_fields=['status', 'stdout', 'stderr', 'completed_at']
        )

        logger.info(
            f'Command {execution.command_name} completed successfully '
            f'(execution_id={execution_id}, '
            f'duration={execution.duration_display})'
        )

    except Exception as exc:
        # Capture error information
        execution.stderr = stderr_capture.getvalue()
        execution.error_message = str(exc)
        execution.retry_count += 1

        # Attempt retry if within limit
        if self.request.retries < self.max_retries:
            execution.status = 'retrying'
            execution.save(
                update_fields=[
                    'stderr',
                    'error_message',
                    'retry_count',
                    'status',
                ]
            )
            logger.warning(
                f'Command {execution.command_name} failed, retrying '
                f'(attempt {self.request.retries + 1}/{self.max_retries})'
            )
            raise self.retry(exc=exc)
        else:
            # Final failure
            execution.status = 'failed'
            execution.completed_at = timezone.now()
            execution.save(
                update_fields=[
                    'status',
                    'stderr',
                    'error_message',
                    'completed_at',
                    'retry_count',
                ]
            )
            logger.error(
                f'Command {execution.command_name} failed after '
                f'{self.max_retries} retries: {exc}'
            )
