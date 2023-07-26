from django.db import models
from django.conf import settings

DRAFT = 'Draft'
PENDING = 'Pending'
LATEST = 'Latest'
ARCHIVED = 'Archived'


class DatasetVersion(models.Model):
    STATUS_CHOICES = (
        (DRAFT, DRAFT),
        (PENDING, PENDING),
        (LATEST, LATEST),
        (ARCHIVED, ARCHIVED),
    )

    version = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    status = models.CharField(
        choices=STATUS_CHOICES,
        max_length=50,
        null=False,
        blank=False
    )

    version_name = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    source = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.dataset if self.dataset else ""} - ' \
               f'{self.version}'
