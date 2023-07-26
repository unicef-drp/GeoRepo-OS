from django.db import models
from django.conf import settings


class IdType(models.Model):
    name = models.CharField(
        default='',
        blank=False,
        null=False,
        max_length=128
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name
