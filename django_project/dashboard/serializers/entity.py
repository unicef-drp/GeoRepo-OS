from rest_framework import serializers
from django.db.models import Q
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.models.entity import EntityName, EntityId
from dashboard.models import EntitiesUserConfig


class DasboardDatasetEntityListSerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    name = serializers.CharField(source='label')
    default_code = serializers.CharField(source='internal_code')
    ucode = serializers.CharField(source='unique_code')
    concept_ucode = serializers.CharField()
    updated = serializers.DateTimeField(source='start_date')
    rev = serializers.CharField(source='revision_number')
    status = serializers.SerializerMethodField()
    centroid = serializers.SerializerMethodField()
    privacy_level = serializers.SerializerMethodField(source='privacy_level')
    other_name = serializers.SerializerMethodField(source='other_name')
    other_id = serializers.SerializerMethodField(source='other_id')
    layer_file = serializers.SerializerMethodField(source='layer_file')
    approved_by = serializers.SerializerMethodField(source='approved_by')
    is_latest = serializers.SerializerMethodField(source='is_latest')

    def get_country(self, obj):
        return obj['country']

    def get_type(self, obj):
        return obj['type']

    def get_status(self, obj):
        return obj['status']

    def get_centroid(self, obj):
        return obj['centroid']

    def get_privacy_level(self, obj):
        return obj['privacy_level']

    def get_other_name(self, obj):
        return obj['other_name']

    def get_other_id(self, obj):
        return obj['other_id']

    def get_layer_file(self, obj):
        return obj['layer_file']

    def get_approved_by(self, obj):
        return obj['approved_by']

    def get_is_latest(self, obj):
        return str(obj['is_latest'])


    class Meta:
        model = GeographicalEntity
        fields = [
            'id',
            'country',
            'level',
            'type',
            'name',
            'default_code',
            'ucode',
            'concept_ucode',
            'updated',
            'rev',
            'status',
            'centroid',
            'unique_code_version',
            'is_latest',
            'approved_date',
            'geometry',
            'source',
            'admin_level_name',
            'approved_by',
            'parent',
            'layer_file',
            'ancestor',
            'privacy_level',
            'other_name',
            'other_id'
        ]


class EntityItemConceptUCodeSerializer(DasboardDatasetEntityListSerializer):
    code = serializers.SerializerMethodField()
    valid_from = serializers.DateTimeField(source='start_date')

    def get_code(self, obj: GeographicalEntity):
        return obj.ucode

    def get_type(self, obj: GeographicalEntity):
        return obj.type.label

    def get_status(self, obj: GeographicalEntity):
        return 'Approved' if obj.is_approved else 'Pending'

    class Meta:
        model = GeographicalEntity
        fields = [
            'id',
            'level',
            'type',
            'name',
            'default_code',
            'code',
            'valid_from',
            'rev',
            'status'
        ]


class EntityConceptUCodeSerializer(serializers.ModelSerializer):
    dataset_id = serializers.SerializerMethodField()
    dataset_uuid = serializers.SerializerMethodField()
    module_name = serializers.SerializerMethodField()
    source_name = serializers.SerializerMethodField()
    concept_ucode = serializers.SerializerMethodField()
    concept_uuid = serializers.SerializerMethodField()
    entities = serializers.SerializerMethodField()
    session = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    dataset_name = serializers.SerializerMethodField()

    def get_dataset_id(self, obj: Dataset):
        return obj.id

    def get_dataset_name(self, obj: Dataset):
        return obj.label

    def get_dataset_uuid(self, obj: Dataset):
        return obj.uuid

    def get_module_name(self, obj: Dataset):
        return obj.module.name

    def get_source_name(self, obj: Dataset):
        if obj.style_source_name:
            return obj.style_source_name
        return str(obj.uuid)

    def get_concept_ucode(self, obj: Dataset):
        return self.context['concept_ucode']

    def get_entities(self, obj: Dataset):
        entities = self.context['entities']
        return EntityItemConceptUCodeSerializer(
            entities,
            many=True
        ).data

    def get_concept_uuid(self, obj: Dataset):
        entities = self.context['entities']
        entity = entities.first()
        return entity.uuid if entity else ''

    def get_country(self, obj: Dataset):
        entities = self.context['entities']
        entity = entities.first()
        if entity:
            return entity.ancestor.label if entity.ancestor else entity.label
        return '-'

    def get_session(self, obj: Dataset):
        # fetch from recent one if any
        last_config = EntitiesUserConfig.objects.filter(
            dataset=obj,
            user=self.context['user']
        ).filter(
            Q(query_string__isnull=True) |
            Q(query_string__exact='')
        ).filter(
            concept_ucode__isnull=False
        ).order_by('updated_at').last()
        if last_config:
            # no need to use filters
            last_config.filters = {}
            last_config.concept_ucode = self.context['concept_ucode']
            last_config.save()
            return str(last_config.uuid)
        config = EntitiesUserConfig.objects.create(
            dataset=obj,
            user=self.context['user'],
            filters={},
            concept_ucode=self.context['concept_ucode']
        )
        return str(config.uuid)

    class Meta:
        model = Dataset
        fields = [
            'dataset_id',
            'dataset_uuid',
            'module_name',
            'source_name',
            'concept_ucode',
            'entities',
            'country',
            'concept_uuid',
            'dataset_name',
            'session'
        ]


class EntityEditSerializer(serializers.ModelSerializer):
    names = serializers.SerializerMethodField()
    codes = serializers.SerializerMethodField()

    def get_names(self, obj):
        names = EntityName.objects.filter(geographical_entity=obj)
        return [{
            'id':
            'is'
        }]

    class Meta:
        model = GeographicalEntity
        fields = [
            'names',
            'codes',
            'type',
            'source',
            'privacy_level'
        ]