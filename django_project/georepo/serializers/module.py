from drf_yasg import openapi
from georepo.serializers.common import APIResponseModelSerializer
from georepo.models.module import Module


class ModuleSerializer(APIResponseModelSerializer):

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Module',
            'properties': {
                'name': openapi.Schema(
                    title='Module Name',
                    type=openapi.TYPE_STRING
                ),
                'description': openapi.Schema(
                    title='Module description',
                    type=openapi.TYPE_STRING
                ),
                'uuid': openapi.Schema(
                    title='Module UUID',
                    type=openapi.TYPE_STRING
                )
            },
            'required': ['name', 'uuid'],
            'example': {
                'name': 'Admin Boundaries',
                'description': 'Admin Boundaries Module',
                'uuid': '4078cbf8-f773-4bd8-9450-5685d86f8b27'
            }
        }

        model = Module
        fields = [
            'name',
            'description',
            'uuid'
        ]
