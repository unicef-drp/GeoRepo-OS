from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.utils.celery_helper import get_task_status


class CheckTaskStatus(AzureAuthRequiredMixin, APIView):
    """Check task status."""
    permission_classes = (
        IsAuthenticated,
    )

    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task_id', '')
        status = get_task_status(task_id)
        return Response(
            status=200,
            data={
                'status': status
            }
        )
