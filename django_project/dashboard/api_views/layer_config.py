from datetime import datetime

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models import (
    LayerConfig, LayerUploadSession
)
from dashboard.serializers.layer_config import (
    DetailLayerConfigSerializer, ListLayerConfigSerializer
)


class SaveLayerConfig(AzureAuthRequiredMixin, APIView):
    """
    Save Layer Config Object
    """

    def post(self, request, format=None):
        upload_session = get_object_or_404(
            LayerUploadSession,
            id=request.data.get('layer_upload_session', '')
        )
        layer_config = LayerConfig.objects.create(
            name=request.data.get('name'),
            level=request.data.get('level'),
            dataset=upload_session.dataset,
            created_by=self.request.user,
            created_at=datetime.now,
            location_type_field=request.data.get('location_type_field', ''),
            parent_id_field=request.data.get('parent_id_field', ''),
            source_field=request.data.get('source_field', ''),
            name_fields=request.data.get('name_fields'),
            id_fields=request.data.get('id_fields'),
            entity_type=request.data.get('entity_type', ''),
            boundary_type=request.data.get('boundary_type', ''),
            privacy_level_field=request.data.get('privacy_level_field', ''),
            privacy_level=request.data.get('privacy_level', ''),
        )

        return Response(status=200, data=DetailLayerConfigSerializer(
            layer_config
        ).data)


class LayerConfigList(AzureAuthRequiredMixin, APIView):
    """
    Get list of layer config per admin level ordered by creation date
    """

    def get(self, request, format=None):
        level = request.GET.get('level')
        layer_configs = LayerConfig.objects.filter(
            level=level
        ).order_by('-created_at')
        serializer = ListLayerConfigSerializer(
            layer_configs, many=True)
        return Response(
            serializer.data
        )


class LoadLayerConfig(AzureAuthRequiredMixin, APIView):
    """
    Load layer config by Id
    """

    def get(self, request, format=None):
        id = request.GET.get('id')
        layer_config = get_object_or_404(
            LayerConfig,
            id=id
        )
        serializer = DetailLayerConfigSerializer(layer_config)
        return Response(status=200, data=serializer.data)
