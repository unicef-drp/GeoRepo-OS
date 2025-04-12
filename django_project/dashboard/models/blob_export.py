from django.db import models

from georepo.models import BaseTaskRequest


class BlobExportRequest(BaseTaskRequest):
    """Class that represents the blob export request."""

    path = models.CharField(
        max_length=512,
        help_text='Path to the blob to be exported',
    )

    output_path = models.CharField(
        max_length=512,
        help_text='Path to the zip output file',
        null=True,
        blank=True
    )

    size = models.BigIntegerField(
        help_text='Size of the output file',
        null=True,
        blank=True
    )
