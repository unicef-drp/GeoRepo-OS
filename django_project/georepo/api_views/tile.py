import os
import io
import gzip
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse
from wsgiref.util import FileWrapper
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from azure.core.exceptions import ResourceNotFoundError
from georepo.utils.azure_blob_storage import StorageContainerClient


class TileAPIView(APIView):
    permission_classes = [AllowAny]

    def check_pending_resource_generation(self, resource_uuid, z):
        cache_key = f'{resource_uuid}-{z}-pending-tile'
        return cache.get(cache_key, False)

    def store_mvt_cache(self, resource_uuid, z, x, y, data):
        bytesbuffer = io.BytesIO()
        with gzip.GzipFile(fileobj=bytesbuffer, mode='w') as w:
            w.write(data)
        bytes_result = bytesbuffer.getvalue()
        if settings.USE_AZURE:
            if not StorageContainerClient:
                return
            layer_tiles_dest = (
                f'layer_tiles/{resource_uuid}/{z}/{x}/{y}'
            )
            StorageContainerClient.upload_blob(layer_tiles_dest, bytes_result)
        else:
            vector_tile_path = os.path.join(
                settings.LAYER_TILES_PATH,
                resource_uuid,
                f'{z}',
                f'{x}',
                f'{y}'
            )
            with open(vector_tile_path, 'wb') as f:
                f.write(bytes_result)
        return bytes_result

    def generate_tile(self, sql):
        tile = bytes()
        with connection.cursor() as cursor:
            raw_sql = (
                'SELECT ({sub_sqls}) AS data'
            ).format(sub_sqls=sql)
            cursor.execute(raw_sql)
            row = cursor.fetchone()
            tile = row[0]
        return tile

    def do_run_query(self, z_param, x_param, y_param,
                     cache_value):
        z = int(z_param)
        x = int(x_param)
        y = int(y_param)
        sqls = []
        for level in cache_value:
            sql = cache_value[level]
            q = sql.format(
                bbox_param=f'TileBBox({z}, {x}, {y}, 3857)',
                zoom_param=f'{z}',
                intersects_param=f'TileBBox({z}, {x}, {y}, 4326)'
            )
            fsql = (
                '(SELECT ST_AsMVT(q,\'{mvt_name}\',4096,\'geometry\',\'id\') '
                'AS data '
                'FROM ({query}) AS q)'
            ).format(
                mvt_name=f'Level-{level}',
                query=q
            )
            sqls.append(fsql)
        sub_sqls = '||'.join(sqls)
        return self.generate_tile(sub_sqls)

    def get_tile_from_live_cache(self, resource_uuid, z, x, y):
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
        return None

    def get(self, *args, **kwargs):
        resource_uuid = kwargs.get('resource', None)
        z = kwargs.get('z')
        x = kwargs.get('x')
        y = kwargs.get('y')
        response = self.get_tile_from_live_cache(resource_uuid, z, x, y)
        if response:
            return response
        # try to check if resource is in pending generation
        cache_value = self.check_pending_resource_generation(
            resource_uuid, z)
        if cache_value:
            # generate live VT
            tile = self.do_run_query(z, x, y, cache_value)
            if len(tile):
                tile_bytes = self.store_mvt_cache(resource_uuid, z, x, y, tile)
                response = HttpResponse(
                    tile_bytes,
                    status=200,
                    content_type='application/octet-stream'
                )
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = len(tile_bytes)
                response['Content-Disposition'] = (
                    f'attachment; filename={y}.pbf'
                )
                return response
        return Response(status=404, data={
            'detail': 'Not Found'
        })
