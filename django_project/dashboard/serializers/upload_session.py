from rest_framework import serializers
from rest_framework_csv import renderers as r
from django.db.models import IntegerField
from django.db.models.functions import Cast
from georepo.models.entity import GeographicalEntity
from georepo.models.boundary_type import BoundaryType
from dashboard.models import (
    LayerUploadSession, LayerFile, CANCELED, DONE, REVIEWING
)


class UploadSessionSerializer(serializers.ModelSerializer):
    upload_date = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()
    form = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    level_0_entity = serializers.SerializerMethodField()

    def get_dataset(self, obj: LayerUploadSession):
        if obj.dataset:
            return obj.dataset.label
        return '-'

    def get_type(self, obj: LayerUploadSession):
        if obj.dataset and obj.dataset.module:
            return obj.dataset.module.name
        return ''

    def get_form(self, obj: LayerUploadSession):
        if (
            obj.last_step is not None and
                obj.status != CANCELED and
                obj.status != DONE and
                obj.status != REVIEWING
        ):
            return f'?session={obj.id}&step={obj.last_step}&' \
                   f'dataset={obj.dataset.id}'
        return f'?session={obj.id}&step=0&' \
            f'dataset={obj.dataset.id}'

    def get_upload_date(self, obj: LayerUploadSession):
        return obj.started_at

    def get_uploaded_by(self, obj: LayerUploadSession):
        if obj.uploader and obj.uploader.first_name:
            name = obj.uploader.first_name
            if obj.uploader.last_name:
                name = f'{name} {obj.uploader.last_name}'
            return name
        return '-'

    def get_level_0_entity(self, obj: LayerUploadSession):
        level_0_entities = list(
            obj.entityuploadstatus_set.filter(
                revised_geographical_entity__label__isnull=False
            ).values_list('revised_geographical_entity__label', flat=True)
        )
        entity_uploads_str = ', '.join(level_0_entities)
        entity_uploads_str = entity_uploads_str[:20] if \
            len(entity_uploads_str) > 12 else entity_uploads_str
        if len(level_0_entities) > 1:
            entity_uploads_str += '...'
        elif len(level_0_entities) == 1 and \
            entity_uploads_str != level_0_entities[0]:
            entity_uploads_str += '...'
        return entity_uploads_str

    class Meta:
        model = LayerUploadSession
        fields = [
            'id',
            'dataset',
            'type',
            'upload_date',
            'uploaded_by',
            'status',
            'form',
            'level_0_entity'
        ]


class LayerFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    def get_file_name(self, obj: LayerFile):
        if obj.layer_file:
            return obj.layer_file.name.split('/')[-1]
        return '-'

    class Meta:
        model = LayerFile
        fields = [
            'meta_id',
            'file_name',
            'level',
            'processed',
            'entity_type'
        ]


class DetailUploadSessionSerializer(serializers.ModelSerializer):
    levels = serializers.SerializerMethodField()
    uploader = serializers.SerializerMethodField()
    dataset_creator = serializers.SerializerMethodField()
    first_upload = serializers.SerializerMethodField()
    is_read_only = serializers.SerializerMethodField()
    dataset_uuid = serializers.SerializerMethodField()
    dataset_style_source = serializers.SerializerMethodField()
    revised_entity_uuid = serializers.SerializerMethodField()
    ancestor_bbox = serializers.SerializerMethodField()
    types = serializers.SerializerMethodField()
    revision_number = serializers.SerializerMethodField()
    dataset_name = serializers.SerializerMethodField()
    module_name = serializers.SerializerMethodField()

    def get_first_upload(self, obj: LayerUploadSession):
        return (
            obj.dataset.geographicalentity_set.all().count() == 0
        )

    def get_dataset_creator(self, obj: LayerUploadSession):
        if obj.dataset.created_by:
            return obj.dataset.created_by.id
        return ''

    def get_uploader(self, obj):
        return obj.uploader.username if obj.uploader else '-'

    def get_levels(self, obj):
        layer_files = LayerFile.objects.filter(
            layer_upload_session=obj
        )
        if 'max_level' in self.context and self.context['max_level']:
            max_level = int(self.context['max_level'])
            layer_files = layer_files.annotate(
                level_int=Cast('level', IntegerField())
            ).filter(
                level_int__lte=max_level
            )
        layer_files = layer_files.order_by('level')
        return LayerFileSerializer(layer_files, many=True).data

    def get_is_read_only(self, obj: LayerUploadSession):
        return obj.is_read_only()

    def get_dataset_uuid(self, obj: LayerUploadSession):
        return obj.dataset.uuid

    def get_dataset_style_source(self, obj: LayerUploadSession):
        return (
            obj.dataset.style_source_name if
            obj.dataset.style_source_name else str(obj.dataset.uuid)
        )

    def get_revised_entity_uuid(self, obj: LayerUploadSession):
        if (
            'revised_entity' in self.context and
            self.context['revised_entity']
        ):
            revised_entity = self.context['revised_entity']
            return revised_entity.uuid_revision
        return ''

    def get_ancestor_bbox(self, obj: LayerUploadSession):
        if (
            'revised_entity' in self.context and
            self.context['revised_entity']
        ):
            revised_entity = self.context['revised_entity']
            return revised_entity.geometry.extent
        return []

    def get_types(self, obj: LayerUploadSession):
        layer_files = LayerFile.objects.filter(
            layer_upload_session=obj
        )
        boundary_types = []
        if 'revision_number' in self.context:
            revision_number = self.context['revision_number']
            types = GeographicalEntity.objects.filter(
                layer_file__in=layer_files,
                revision_number=revision_number
            ).order_by('type').values('type').distinct()
            boundary_types = BoundaryType.objects.filter(
                type__in=types,
                dataset=obj.dataset
            ).order_by('value').values_list('value', flat=True)
        return boundary_types

    def get_revision_number(self, obj: LayerUploadSession):
        revision_number = 1
        if 'revision_number' in self.context:
            revision_number = self.context['revision_number']
        return revision_number

    def get_dataset_name(self, obj: LayerUploadSession):
        return obj.dataset.label

    def get_module_name(self, obj: LayerUploadSession):
        return obj.dataset.module.name

    class Meta:
        model = LayerUploadSession
        fields = [
            'id',
            'uploader',
            'dataset',
            'status',
            'started_at',
            'modified_at',
            'levels',
            'description',
            'source',
            'dataset_creator',
            'first_upload',
            'is_read_only',
            'is_historical_upload',
            'historical_start_date',
            'historical_end_date',
            'dataset_uuid',
            'revised_entity_uuid',
            'dataset_style_source',
            'ancestor_bbox',
            'types',
            'revision_number',
            'tolerance',
            'overlaps_threshold',
            'gaps_threshold',
            'dataset_name',
            'module_name'
        ]


class ValidationCSVRenderer(r.CSVRenderer):
    header = ['level', 'name', 'entity_id', 'error']
