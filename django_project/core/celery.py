from __future__ import absolute_import, unicode_literals

import os
import logging
from celery import Celery, signals
from celery.utils.serialization import strtobool
from celery.worker.control import inspect_command
from django.utils import timezone


logger = logging.getLogger(__name__)


# set the default Django settings module for the 'celery' program.
# this is also used in manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Get the base REDIS URL, default to redis' default
BASE_REDIS_URL = (
    f'redis://default:{os.environ.get("REDIS_PASSWORD", "")}'
    f'@{os.environ.get("REDIS_HOST", "")}',
)

app = Celery('georepo')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
# set visibility timeout (Redis) to 3 hours
# https://stackoverflow.com/questions/27310899/
# celery-is-rerunning-long-running-completed-tasks-over-and-over
app.conf.broker_transport_options = {'visibility_timeout': 3 * 3600}


def create_celery_logger_handler(logger, propagate):
    # set azure sdk log to warning level
    az_logger = logging.getLogger('azure')
    az_logger.setLevel(logging.WARNING)


@signals.after_setup_task_logger.connect
def after_setup_celery_task_logger(logger, **kwargs):
    """ This function sets the 'celery.task' logger handler and formatter """
    create_celery_logger_handler(logger, True)


@signals.after_setup_logger.connect
def after_setup_celery_logger(logger, **kwargs):
    """ This function sets the 'celery' logger handler and formatter """
    create_celery_logger_handler(logger, False)


@signals.after_task_publish.connect
def task_sent_handler(sender=None, headers=None, body=None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    from georepo.utils.celery_helper import on_task_queued_or_running
    # information about task are located in headers for task messages
    # using the task protocol version 2.
    info = headers if 'task' in headers else body
    task_id = info['id']
    task_args = info['argsrepr'] if 'argsrepr' in info else ''
    bg_task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': info['task'],
            'last_update': timezone.now(),
            'parameters': task_args
        }
    )
    on_task_queued_or_running(bg_task)


@signals.task_received.connect
def task_received_handler(sender, request=None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    task_id = request.id if request else None
    task_args = request.args
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': request.name if request else '',
            'last_update': timezone.now(),
            'parameters': str(task_args)
        }
    )
    task.last_update = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.QUEUED
    task.save(update_fields=['last_update', 'status'])


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None,
                        args=None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    from georepo.utils.celery_helper import on_task_queued_or_running
    task, is_created = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender.name if sender else '',
            'parameters': str(args),
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.started_at = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.RUNNING
    task.save(update_fields=['last_update', 'started_at', 'status'])
    on_task_queued_or_running(task)


@signals.task_success.connect
def task_success_handler(sender, **kwargs):
    from georepo.models.background_task import BackgroundTask
    from georepo.utils.celery_helper import on_task_success
    task_id = sender.request.id
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender.name if sender else '',
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.finished_at = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.COMPLETED
    task.save(update_fields=['last_update', 'finished_at', 'status'])
    on_task_success(task)


@signals.task_failure.connect
def task_failure_handler(sender, task_id=None, args=None,
                         exception=None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender,
            'parameters': str(args),
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.finished_at = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.STOPPED
    task.errors = str(exception)
    task.save(
        update_fields=['last_update', 'finished_at', 'status', 'errors']
    )


@signals.task_revoked.connect
def task_revoked_handler(sender, request = None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    task_id = request.id if request else None
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender.name if sender else '',
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.CANCELLED
    task.save(update_fields=['last_update', 'status'])


@signals.task_internal_error.connect
def task_internal_error_handler(sender, task_id=None,
                                exception=None, **kwargs):
    from georepo.models.background_task import BackgroundTask
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender.name if sender else '',
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.status = BackgroundTask.BackgroundTaskStatus.STOPPED
    task.errors = str(exception)
    task.save(
        update_fields=['last_update', 'status', 'errors']
    )


@signals.task_retry.connect
def task_retry_handler(sender, reason, **kwargs):
    from georepo.models.background_task import BackgroundTask
    task_id = sender.request.id
    logger.info(f'on task_retry_handler {task_id}')
    task, _ = BackgroundTask.objects.get_or_create(
        task_id=task_id,
        defaults={
            'name': sender.name if sender else '',
            'last_update': timezone.now(),
        }
    )
    task.last_update = timezone.now()
    task.celery_retry += 1
    task.celery_last_retry_at = timezone.now()
    task.celery_retry_reason = str(reason)
    task.save(
        update_fields=['last_update', 'celery_retry',
                       'celery_last_retry_at', 'celery_retry_reason']
    )


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.broker_url = BASE_REDIS_URL

# this allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'


@inspect_command(
    alias='dump_conf',
    signature='[include_defaults=False]',
    args=[('with_defaults', strtobool)],
)
def conf(state, with_defaults=False, **kwargs):
    """
    This overrides the `conf` inspect command to effectively disable it.
    This is to stop sensitive configuration info appearing in e.g. Flower.
    (Celery makes an attempt to remove sensitive info,but it is not foolproof)
    """
    return {'error': 'Config inspection has been disabled.'}
