import django
from .celery import app as celery_app  # noqa


django.setup()
