# coding=utf-8
"""
GeoRepo.

.. note:: Mixin for API Tracking
"""

import json
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework_tracking.base_mixins import BaseLoggingMixin


class APILoggingMixin(BaseLoggingMixin):
    """Mixin to log GeoRepo API request."""

    CACHE_KEY = 'georepo_logs_queue'

    def set_output_file_size(self, size):
        """Set output file size."""
        if self.log is not None:
            self.log['output_file_size'] = size

    def handle_log(self):
        """Store log to redis queue cache."""
        # remove data and response
        self.log['data'] = None
        self.log['response'] = None
        if self.log.get('user', None):
            # replace with user id
            self.log['user'] = self.log['user'].id
        try:
            cache._cache.get_client().rpush(
                self.CACHE_KEY,
                json.dumps(self.log, cls=DjangoJSONEncoder)
            )
        except Exception:  # noqa
            pass
