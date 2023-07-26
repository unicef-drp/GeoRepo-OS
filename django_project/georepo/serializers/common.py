from collections import OrderedDict
from rest_framework import serializers


class APIErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class APIResponseModelSerializer(serializers.ModelSerializer):
    """
    Remove empty fields
    """
    remove_empty_fields = True

    def is_field_empty(self, key, value):
        return value is None or value == '' or value == '-'

    def to_representation(self, instance):
        representation = (
            super(APIResponseModelSerializer, self).to_representation(instance)
        )
        results = []
        for k, v in representation.items():
            if self.remove_empty_fields:
                if not self.is_field_empty(k, v):
                    results.append((k, v))
            else:
                results.append((k, v))
        return OrderedDict(results)
