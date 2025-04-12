from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from georepo.models import BaseTaskRequest
from georepo.utils.azure_blob_storage import StorageContainerClient


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

    def download(self, directory):
        """Download files in Blob storage path to directory."""
        pass


@receiver(post_delete, sender=BlobExportRequest)
def post_delete_export_request(sender, instance, **kwargs):
    """Delete output file in blob storage."""
    if instance.output_path:
        try:
            bc = StorageContainerClient.get_blob_client(
                blob=instance.output_path
            )
            bc.delete_blob()
        except Exception as e:
            # Handle exception if needed
            print(f'Error deleting blob: {e}')
