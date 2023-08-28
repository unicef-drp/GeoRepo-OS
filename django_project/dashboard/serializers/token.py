from rest_framework import serializers
from core.models.token_detail import ApiKey


class ApiKeySerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()

    def get_user_id(self, obj: ApiKey):
        return obj.token.user.id if obj.token else ''

    def get_created(self, obj: ApiKey):
        return obj.token.created

    class Meta:
        model = ApiKey
        fields = [
            'user_id',
            'created',
            'platform',
            'owner',
            'contact',
            'is_active'
        ]
