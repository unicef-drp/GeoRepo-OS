from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models import (
    Notification,
    Maintenance
)
from dashboard.serializers.notification import (
    ListNotificationSerializer,
    DetailMaintenanceSerializer
)

CHECK_MAINTENANCE_IN_MINUTES = 10


class NotificationList(AzureAuthRequiredMixin, APIView):
    """
    Fetch notification list for logged-in user
    After fetching, the list will be removed
    """

    def get_notification_list(self):
        notifications = Notification.objects.filter(
            recipient=self.request.user
        ).order_by('created_at')
        serializer = ListNotificationSerializer(
            notifications, many=True)
        return serializer.data

    def get_maintenance(self):
        current_datetime = timezone.now()
        maintenance = Maintenance.objects.filter(
            scheduled_from_date__lte=current_datetime
        ).filter(
            Q(scheduled_end_date__isnull=True) |
            Q(scheduled_end_date__gte=current_datetime)
        ).order_by('scheduled_from_date')
        serializer = DetailMaintenanceSerializer(maintenance.first())
        return maintenance.exists(), serializer.data

    def get(self, request, format=None):
        has_maintenance, maintenance = self.get_maintenance()
        response = Response(
            status=200,
            data={
                'notifications': self.get_notification_list(),
                'has_maintenance': has_maintenance,
                'maintenance': maintenance
            }
        )
        Notification.objects.filter(
            recipient=self.request.user
        ).delete()
        return response
