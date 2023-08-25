from __future__ import absolute_import, unicode_literals

import os
import logging
from celery import Celery, signals


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


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.broker_url = BASE_REDIS_URL

# this allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'
