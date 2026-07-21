# coding=utf-8
"""
GeoRepo.

.. note:: Unit tests for CommandExecution and execute_django_command task
"""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from core.models import CommandExecution
from core.tasks import execute_django_command


class CommandExecutionModelTest(TestCase):
    """Test CommandExecution model."""

    def test_create_command_execution(self):
        """Test creating a CommandExecution record."""
        execution = CommandExecution.objects.create(
            command_name='test_command',
            command_args=['arg1', 'arg2'],
            command_kwargs={'key1': 'value1'},
            celery_task_id='test-task-id-123',
            triggered_by='test_user'
        )

        self.assertEqual(execution.command_name, 'test_command')
        self.assertEqual(execution.command_args, ['arg1', 'arg2'])
        self.assertEqual(execution.command_kwargs, {'key1': 'value1'})
        self.assertEqual(execution.status, 'pending')
        self.assertEqual(execution.triggered_by, 'test_user')

    def test_duration_property(self):
        """Test duration calculation."""
        execution = CommandExecution.objects.create(
            command_name='test_command',
            celery_task_id='test-task-id-124',
            started_at=timezone.now(),
        )

        # No completed_at yet
        self.assertIsNone(execution.duration)

        # Add completed_at
        execution.completed_at = (
            execution.started_at + timedelta(seconds=65)
        )
        self.assertEqual(execution.duration, 65.0)

    def test_duration_display(self):
        """Test duration display formatting."""
        execution = CommandExecution.objects.create(
            command_name='test_command',
            celery_task_id='test-task-id-125',
        )

        # No duration
        self.assertEqual(execution.duration_display, 'N/A')

        # Seconds
        execution.started_at = timezone.now()
        execution.completed_at = (
            execution.started_at + timedelta(seconds=45)
        )
        self.assertEqual(execution.duration_display, '45.00s')

        # Minutes
        execution.completed_at = (
            execution.started_at + timedelta(seconds=120)
        )
        self.assertEqual(execution.duration_display, '2.00m')

        # Hours
        execution.completed_at = (
            execution.started_at + timedelta(seconds=7200)
        )
        self.assertEqual(execution.duration_display, '2.00h')

    def test_str_representation(self):
        """Test string representation."""
        execution = CommandExecution.objects.create(
            command_name='test_command',
            celery_task_id='test-task-id-126',
            status='success'
        )

        # String representation includes first 8 chars of task ID
        str_repr = str(execution)
        self.assertIn('test_command', str_repr)
        self.assertIn('success', str_repr)
        self.assertIn('test-tas', str_repr)

    def test_multiple_objects_with_empty_celery_id(self):
        """Test creating multiple objects with empty celery_task_id."""
        execution1 = CommandExecution.objects.create(
            command_name='test_command_1',
            celery_task_id='',
            triggered_by='user1'
        )
        execution2 = CommandExecution.objects.create(
            command_name='test_command_2',
            celery_task_id='',
            triggered_by='user2'
        )
        execution3 = CommandExecution.objects.create(
            command_name='test_command_3',
            celery_task_id='',
            triggered_by='user3'
        )

        self.assertEqual(
            CommandExecution.objects.filter(celery_task_id='').count(), 3
        )
        self.assertIsNotNone(execution1.id)
        self.assertIsNotNone(execution2.id)
        self.assertIsNotNone(execution3.id)

        self.assertNotEqual(execution1.id, execution2.id)
        self.assertNotEqual(execution1.id, execution3.id)
        self.assertNotEqual(execution2.id, execution3.id)


class ExecuteDjangoCommandTaskTest(TestCase):
    """Test execute_django_command celery task."""

    @mock.patch('core.tasks.command_execution.call_command')
    def test_execute_django_command_captures_output(
        self, mock_call_command
    ):
        """Test that the task properly captures stdout/stderr."""
        execution = CommandExecution.objects.create(
            command_name='supervisor',
            command_args=['status'],
            command_kwargs={},
            celery_task_id='test-task-id-127',
            triggered_by='test_user'
        )

        def mock_call_cmd(cmd_name, *args, **kwargs):
            stdout = kwargs.get('stdout')
            if stdout:
                stdout.write('celery-worker RUNNING\n')

        mock_call_command.side_effect = mock_call_cmd

        # Use apply() to bypass Celery and execute synchronously with a
        # mocked request/task id.
        execute_django_command.apply(
            args=[execution.id],
            task_id='celery-task-123'
        )

        execution.refresh_from_db()

        self.assertEqual(execution.status, 'success')
        self.assertIn('celery-worker RUNNING', execution.stdout)
        self.assertIsNotNone(execution.started_at)
        self.assertIsNotNone(execution.completed_at)
        self.assertEqual(execution.celery_task_id, 'celery-task-123')

    @mock.patch('core.tasks.command_execution.call_command')
    def test_execute_django_command_marks_failed_after_retries(
        self, mock_call_command
    ):
        """Test that the task marks execution as failed after retries."""
        execution = CommandExecution.objects.create(
            command_name='supervisor',
            command_args=['restart', 'bogus-name'],
            command_kwargs={},
            celery_task_id='test-task-id-128',
            triggered_by='test_user'
        )

        mock_call_command.side_effect = Exception('unknown worker')

        # apply() runs the task eagerly/synchronously, so retries raised
        # via self.retry() are executed inline until max_retries is hit.
        execute_django_command.apply(
            args=[execution.id],
            task_id='celery-task-129'
        )

        execution.refresh_from_db()

        self.assertEqual(execution.status, 'failed')
        self.assertIn('unknown worker', execution.error_message)
        self.assertIsNotNone(execution.completed_at)
        # initial attempt + 3 retries all increment retry_count
        self.assertEqual(execution.retry_count, 4)
