# coding=utf-8
"""Application config for health check."""
from django.apps import AppConfig


class HealthConfig(AppConfig):
    """Health check application configuration."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'health'
