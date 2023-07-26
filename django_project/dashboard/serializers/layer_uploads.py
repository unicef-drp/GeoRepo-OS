from collections import OrderedDict
from rest_framework import serializers
from georepo.utils.module_import import module_function
from dashboard.models import LayerFile


class LayerUploadSerializer(serializers.ModelSerializer):
    form_valid = serializers.SerializerMethodField()
    is_read_only = serializers.SerializerMethodField()

    def get_form_valid(self, obj: LayerFile):
        dataset = obj.layer_upload_session.dataset
        is_valid_mapping = module_function(
            dataset.module.code_name,
            'field_mapping',
            'is_valid')
        return is_valid_mapping(obj)

    def get_is_read_only(self, obj: LayerFile):
        if 'is_read_only' in self.context:
            return self.context['is_read_only']
        return False

    def to_representation(self, instance: LayerFile):
        representation = (
            super(LayerUploadSerializer, self).to_representation(instance)
        )
        return OrderedDict(
            [(k, list(v))
             if k == 'id_fields' or k == 'name_fields' else (k, v) for k, v in
             representation.items()])

    class Meta:
        model = LayerFile
        fields = '__all__'
