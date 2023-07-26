from uuid import uuid4
import hashlib
import json

from django.db import models
from django.conf import settings


class EntitiesUserConfig(models.Model):

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now_add=True
    )

    uuid = models.UUIDField(
        default=uuid4
    )

    filters = models.JSONField(
        default={},
        blank=True
    )

    query_string = models.TextField(
        null=True,
        blank=True
    )

    concept_ucode = models.TextField(
        null=True,
        blank=True
    )

    def get_filter_viewname(self):
        _filters = self.filters
        # remove empty filter criteria
        if 'updated_at' in _filters:
            del _filters['updated_at']
        for k in list(_filters.keys()):
            if ((k == 'date_from' or k == 'date_to') and
                    _filters[k] is None):
                del _filters[k]
            elif _filters[k] is None or len(_filters[k]) == 0:
                del _filters[k]
        sha = hashlib.sha256()
        sha.update(json.dumps(_filters, sort_keys=True).encode('utf-8'))
        filters_hash = sha.hexdigest()
        return f'filter_ds{self.dataset.id}_{filters_hash}'
