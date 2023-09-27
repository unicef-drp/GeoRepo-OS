from django.core.serializers.json import Serializer as JSONSerializer


class Serializer(JSONSerializer):
    """Exclude geometry from jsonserializer."""

    def handle_field(self, obj, field):
        if (
            obj.__class__.__name__ == 'GeographicalEntity' and
            field.name == 'geometry'
        ):
            pass
        else:
            super().handle_field(obj, field)
