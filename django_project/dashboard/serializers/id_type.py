from rest_framework import serializers

from georepo.models import IdType


class IdTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdType
        fields = [
            'id',
            'name'
        ]
