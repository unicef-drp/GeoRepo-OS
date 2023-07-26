from django.db import models
from django.conf import settings


class DatasetGroup(models.Model):
    module = models.ForeignKey(
        'georepo.Module',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    description = models.TextField(
        null=True,
        blank=True,
        default=''
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.name
