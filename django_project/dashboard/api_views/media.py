import os
import io
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from azure.core.exceptions import ResourceNotFoundError
from georepo.utils.azure_blob_storage import StorageContainerClient
from dashboard.models.entity_upload import EntityUploadStatus


class ErrorReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def build_response(self, file, file_name):
        response = HttpResponse(
            file,
            content_type='text/csv'
        )
        response['Content-Disposition'] = (
            f'attachment; filename={file_name}'
        )
        return response

    def get(self, *args, **kwargs):
        upload_id = kwargs.get('upload_id', None)
        entity_upload = get_object_or_404(
            EntityUploadStatus, id=upload_id
        )
        filename = f'error-report-{entity_upload.id}.csv'
        if settings.USE_AZURE and StorageContainerClient:
            source = f'media/error_reports/{filename}'
            try:
                bc = StorageContainerClient.get_blob_client(blob=source)
                download_stream = bc.download_blob(
                    max_concurrency=2,
                    validate_content=False
                )
                stream = io.BytesIO()
                download_stream.readinto(stream)
                stream.seek(0)
                return self.build_response(stream, filename)
            except ResourceNotFoundError:  # noqa
                pass
        else:
            file_path = os.path.join(
                settings.MEDIA_ROOT,
                'error_reports',
                filename
            )
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    return self.build_response(file, filename)
        return Response(status=404, data={
            'detail': 'Not Found'
        })
