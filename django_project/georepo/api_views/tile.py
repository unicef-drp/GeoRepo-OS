import os
import io
from django.conf import settings
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from azure.core.exceptions import ResourceNotFoundError
from georepo.utils.azure_blob_storage import StorageContainerClient


class TileAPIView(APIView):
    permission_classes = [AllowAny]

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
                bc = StorageContainerClient.get_blob_client(blob=source)
                download_stream = bc.download_blob(
                    max_concurrency=2,
                    validate_content=False
                )
                stream = io.BytesIO()
                download_stream.readinto(stream)
                stream.seek(0)
                return self.build_response(stream, y)
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
                with open(file_path, 'rb') as file:
                    return self.build_response(file, y)
        return Response(status=404, data={
            'detail': 'Not Found'
        })
