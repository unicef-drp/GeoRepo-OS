from rest_framework import serializers
from core.models.token_detail import CustomApiKey


class CustomApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomApiKey
        fields = '__all__'
