from rest_framework import serializers

from dashboard.models import LayerConfig


class DetailLayerConfigSerializer(serializers.ModelSerializer):

    class Meta:
        model = LayerConfig
        fields = '__all__'


class ListLayerConfigSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    dataset_label = serializers.SerializerMethodField()
    created_date = serializers.DateTimeField(source='created_at')

    def get_created_by(self, obj: LayerConfig):
        if obj.created_by and obj.created_by.first_name:
            name = obj.created_by.first_name
            if obj.created_by.last_name:
                name = f'{name} {obj.created_by.last_name}'
            return name
        return '-'

    def get_dataset_label(self, obj: LayerConfig):
        return obj.dataset.label if obj.dataset else '-'

    class Meta:
        model = LayerConfig
        fields = [
            'id',
            'name',
            'level',
            'dataset_label',
            'created_date',
            'created_by'
        ]
