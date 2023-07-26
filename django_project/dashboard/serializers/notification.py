from rest_framework import serializers

from dashboard.models import Notification, Maintenance


class ListNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class DetailMaintenanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Maintenance
        fields = ['id', 'message', 'scheduled_from_date',
                  'scheduled_end_date']
