# coding=utf-8
"""
GeoRepo.

.. note:: Models for API Tracking
"""

from django.db import models
from django.conf import settings
from rest_framework_tracking.base_models import BaseAPIRequestLog


class APIRequestLog(BaseAPIRequestLog):
    """Models that stores GeoRepo API request log."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_api'
    )

    query_params = models.JSONField(
        default=dict,
        null=True,
        blank=True
    )

    output_file_size = models.BigIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text='Size of the output file (if any) in bytes'
    )
