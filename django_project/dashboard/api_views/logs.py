import csv
import subprocess

from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response

from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    EntityUploadStatusLog
)
from dashboard.models.layer_upload_session import LayerUploadSession
from georepo.models.dataset_view import (
    DatasetViewResourceLog,
    DatasetView
)
from dashboard.models.maintenance import StorageLog


class CSVBuffer:
    """An object that implements just the write method of the file-like
    interface.
    """
    def write(self, value):
        """Return the string to write."""
        return value


class ExportLogs(AzureAuthRequiredMixin, APIView):
    """
    Return dataset detail
    """
    permission_classes = [IsAuthenticated]

    def _get_log_object(self, log_type, obj_id):
        logs = []
        name = 'log'
        if log_type == 'dataset_view':
            obj = get_object_or_404(DatasetView, id=obj_id)
            logs = DatasetViewResourceLog.objects.filter(
                Q(dataset_view_resource__dataset_view=obj) |
                Q(dataset_view=obj)
            )
            name = obj.name
        elif log_type == 'upload_session':
            obj = get_object_or_404(LayerUploadSession, id=obj_id)
            logs = EntityUploadStatusLog.objects.filter(
                Q(layer_upload_session=obj) |
                Q(entity_upload_status__upload_session=obj)
            )
            name = (
                f"{obj.dataset.label}-"
                f"{obj.source if obj.source else 'Upload'}"
            )
        elif log_type == 'entity_upload':
            obj = get_object_or_404(EntityUploadStatus, id=obj_id)
            logs = EntityUploadStatusLog.objects.filter(
                entity_upload_status=obj
            )
            entity = (
                obj.revised_geographical_entity.label
                if obj.revised_geographical_entity
                else obj.original_geographical_entity.label
            )
            upload_source = obj.upload_session.source if \
                obj.upload_session.source else \
                'Upload'
            name = (
                f"{obj.upload_session.dataset.label}-"
                f"{upload_source}-"
                f"{entity}")
        return logs, name

    def get(self, request, log_type, obj_id, *args, **kwargs):
        logs, filename = self._get_log_object(log_type, obj_id)

        results: dict = {}
        for log in logs:
            detail: dict = log.logs
            for key, val in detail.items():
                if key in results:
                    avg_time = (results[key]['avg_time'] + val['avg_time']) / 2
                    total_time = results[key]['total_time'] + val['total_time']
                    results[key] = {
                        'count': results[key]['count'] + val['count'],
                        'avg_time': avg_time,
                        'total_time': total_time
                    }
                else:
                    results[key] = val

        writer = csv.writer(CSVBuffer())

        rows = [
            ["Action", "Call Count", "Average Time (s)", "Total Time (s)"]
        ]
        for key, val in results.items():
            key = key.title().replace('_', ' ').replace('.', ' - ')
            if 'Adminboundarymatching' in key:
                key = key.replace(
                    'Adminboundarymatching',
                    'Admin Boundary Matching'
                )
            if 'Validateuploadsession' in key:
                key = key.replace(
                    'Validateuploadsession',
                    'Validate Upload Session'
                )
            rows.append([
                key.title().replace('_', ' '),
                val['count'],
                int(val['avg_time'] * 100) / 100,
                int(val['total_time'] * 100) / 100,
            ])

        response = StreamingHttpResponse(
            (writer.writerow(row) for row in rows),
            content_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}-logs.csv"'
                )
            },
        )

        return response


class CheckDjangoStorageUsage(APIView):
    permission_classes = [IsAdminUser]

    def check_storage(self):
        cmd = ['du -shc /* | sort -h']
        bytes_arr = subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL
        )
        return bytes_arr.decode('utf-8')

    def check_memory(self):
        cmd = ['free', '-m']
        bytes_arr = subprocess.check_output(cmd)
        return bytes_arr.decode('utf-8')

    def get(self, request, *args, **kwargs):
        try:
            StorageLog.objects.create(
                storage_log=self.check_storage(),
                memory_log=self.check_memory()
            )
        except Exception as ex:
            return Response(
                status=400,
                data={
                    'message': str(ex)
                }
            )

        return Response(status=204)
