import csv

from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

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
        if log_type == 'view':
            obj = get_object_or_404(DatasetView, id=obj_id)
            logs = DatasetViewResourceLog.objects.filter(
                Q(dataset_view_resource__dataset_view=obj) |
                Q(dataset_view=obj)
            )
            name = obj.name
        elif log_type == 'layer':
            obj = get_object_or_404(LayerUploadSession, id=obj_id)
            logs = EntityUploadStatusLog.objects.filter(
                Q(layer_upload_session=obj) |
                Q(entity_upload_status__upload_session=obj)
            )
            name = f"{obj.dataset.label}-{obj.source if obj.source else 'Upload'}"
        elif log_type == 'entity':
            obj = get_object_or_404(EntityUploadStatus, id=obj_id)
            logs = EntityUploadStatusLog.objects.filter(
                entity_upload_status=obj
            )
            entity = (
                obj.revised_geographical_entity.label
                if obj.revised_geographical_entity
                else obj.original_geographical_entity.label
            )
            name = (
                f"{obj.upload_session.dataset.label}-"
                f"{obj.upload_session.source if obj.upload_session.source else 'Upload'}-"
                f"{entity}")
        return logs, name

    def get(self, request, log_type, obj_id, *args, **kwargs):
        logs, filename = self._get_log_object(log_type, obj_id)

        results: dict = {}
        for log in logs:
            detail: dict = log.logs
            for key, val in detail.items():
                if key in results:
                    results[key] = {
                        'count': results[key]['count'] + val['count'],
                        'avg_time': (results[key]['avg_time'] + val['avg_time']) / 2,
                        'total_time': results[key]['total_time'] + val['total_time']
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
                key = key.replace('Adminboundarymatching', 'Admin Boundary Matching')
            if 'Validateuploadsession' in key:
                key = key.replace('Validateuploadsession', 'Validate Upload Session')
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
                f"Content-Disposition": f'attachment; filename="{filename}-logs.csv"'
            },
        )

        return response
