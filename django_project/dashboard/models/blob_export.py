from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings

from georepo.models import BaseTaskRequest
import os
from georepo.utils.azure_blob_storage import (
    StorageContainerClient,
    DirectoryClient
)


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
        client = DirectoryClient(
            settings.AZURE_STORAGE,
            settings.AZURE_STORAGE_CONTAINER
        )

        source = self.path
        dest = directory

        blobs = client.ls_files(source, recursive=True)
        if blobs:
            # if source is a directory, dest must also be a directory
            if not source == '' and not source.endswith('/'):
                source += '/'
            if not dest.endswith('/'):
                dest += '/'
            # append the directory name from source to the destination
            dest += os.path.basename(os.path.normpath(source)) + '/'

            blobs = [source + blob for blob in blobs]
            for blob in blobs:
                blob_dest = dest + os.path.relpath(blob, source)
                client.download_file(blob, blob_dest)
        else:
            dest = os.path.join(dest, os.path.basename(source))
            client.download_file(source, dest)


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
