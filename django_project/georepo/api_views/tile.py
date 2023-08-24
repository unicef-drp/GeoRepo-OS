import os
from django.conf import settings
from django.http import HttpResponse
from django.http.response import StreamingHttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from tempfile import SpooledTemporaryFile


class TileAPIView(APIView):
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._service_client = None
        self._client = None

    def _get_service_client(self):
        return BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE
        )

    @property
    def service_client(self):
        if self._service_client is None:
            self._service_client = self._get_service_client()
        return self._service_client

    @property
    def client(self):
        if self._client is None:
            self._client = self.service_client.get_container_client(
                settings.AZURE_STORAGE_CONTAINER
            )
        return self._client
    
    def build_response(self, file, y):
        response = HttpResponse(
            file,
            content_type='application/octet-stream'
        )
        response['Content-Encoding'] = 'gzip'
        response['Content-Disposition'] = (
            f'attachment; filename={y}.pbf'
        )
        return response

    def get(self, *args, **kwargs):
        resource_uuid = kwargs.get('resource', None)
        z = kwargs.get('z')
        x = kwargs.get('x')
        y = kwargs.get('y')
        if settings.USE_AZURE:
            source = f'layer_tiles/{resource_uuid}/{z}/{x}/{y}'
            try:
                with SpooledTemporaryFile() as tmp_file:
                    bc = self.client.get_blob_client(blob=source)
                    download_stream = bc.download_blob()
                    download_stream.readinto(tmp_file)
                    tmp_file.seek(0)
                    return self.build_response(tmp_file, y)
            except ResourceNotFoundError:  # noqa
                pass
        else:
            file_path = os.path.join(
                settings.LAYER_TILES_PATH,
                resource_uuid,
                z,
                x,
                y
            )
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    return self.build_response(file, y)
        return Response(status=404, data={
            'detail': 'Not Found'
        })