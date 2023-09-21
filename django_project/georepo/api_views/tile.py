import os
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from azure.core.exceptions import ResourceNotFoundError
from georepo.utils.azure_blob_storage import StorageContainerClient
from django.http import StreamingHttpResponse
from wsgiref.util import FileWrapper


class TileAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, *args, **kwargs):
        resource_uuid = kwargs.get('resource', None)
        z = kwargs.get('z')
        x = kwargs.get('x')
        y = kwargs.get('y')
        if settings.USE_AZURE and StorageContainerClient:
            source = f'layer_tiles/{resource_uuid}/{z}/{x}/{y}'
            try:
                bc = StorageContainerClient.get_blob_client(blob=source)
                download_stream = bc.download_blob(
                    max_concurrency=2,
                    validate_content=False
                )
                response = StreamingHttpResponse(
                    download_stream.chunks(),
                    status=200,
                    content_type='application/octet-stream'
                )
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = download_stream.size
                response['Content-Disposition'] = (
                    f'attachment; filename={y}.pbf'
                )
                return response
            except ResourceNotFoundError:  # noqa
                pass
        else:
            file_path = os.path.join(
                settings.LAYER_TILES_PATH,
                resource_uuid,
                str(z),
                str(x),
                str(y)
            )
            if os.path.exists(file_path):
                response = StreamingHttpResponse(
                    FileWrapper(open(file_path, 'rb'), 8192),
                    status=200,
                    content_type='application/octet-stream'
                )
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = os.path.getsize(file_path)
                response['Content-Disposition'] = (
                    f'attachment; filename={y}.pbf'
                )
                return response
        return Response(status=404, data={
            'detail': 'Not Found'
        })
