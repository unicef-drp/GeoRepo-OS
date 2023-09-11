from rest_framework import serializers
from django.db.models import Q
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.models.entity import EntityName, EntityId, EntityType
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


class EntityNameListSerializer(serializers.ListSerializer):

    def validate(self, data):
        default_set = set()
        results = []
        for item in data:
            obj = EntityNameSerializer(
                data=item,
                context={
                    'default_set': default_set
                }
            )
            obj.is_valid(raise_exception=True)
            default_set.add(obj.validated_data['default'])
            results.append(obj)

        if default_set == {False}:
            raise serializers.ValidationError(
                'No default name is supplied'
            )

        if len(data) == 0:
            raise serializers.ValidationError(
                'Entity must have at least 1 name'
            )

        return results

    def save(self, entity):
        old_data = EntityName.objects.filter(
            geographical_entity=entity
        )
        items = self.validated_data
        for old in old_data:
            exists = (
                [item for item in items if
                    old.id == item.validated_data['id']]
            )
            if len(exists) == 0:
                old.delete()
        results = []
        for item in items:
            obj = item.save(entity)
            results.append(obj)
        return results


class EntityNameSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    language_id = serializers.IntegerField(allow_null=True)

    def validate_code(self, value):
        stripped_value = value.strip() if value else ''
        return stripped_value

    def validate_default(self, value):
        if 'default_set' in self.context:
            if value is True and value in self.context['default_set']:
                raise serializers.ValidationError(
                    'Duplicate default'
                )
        return value

    def save(self, entity):
        name_id = self.validated_data['id']
        language = self.validated_data['language_id']
        name_value = self.validated_data['name']
        default = self.validated_data['default']
        if name_id > 0:
            try:
                entity_name = EntityName.objects.get(
                    geographical_entity=entity, id=name_id
                )
                entity_name.name = name_value
                entity_name.default = default
                entity_name.language_id = language
                entity_name.save()
            except EntityId.DoesNotExist:
                entity_name = None
        else:
            entity_name = EntityName.objects.create(
                name=name_value,
                default=default,
                geographical_entity=entity,
                language_id=language
            )
        return entity_name

    class Meta:
        model = EntityName
        list_serializer_class = EntityNameListSerializer
        fields = [
            'id', 'default', 'name', 'language_id'
        ]


class EntityCodeListSerializer(serializers.ListSerializer):

    def validate(self, data):
        default_set = set()
        results = []
        for item in data:
            obj = EntityCodeSerializer(
                data=item,
                context={
                    'default_set': default_set
                }
            )
            obj.is_valid(raise_exception=True)
            default_set.add(obj.validated_data['default'])
            results.append(obj)

        if default_set == {False}:
            raise serializers.ValidationError(
                'No default code is supplied'
            )

        if len(data) == 0:
            raise serializers.ValidationError(
                'Entity must have at least 1 code'
            )

        return results

    def save(self, entity):
        old_data = EntityId.objects.filter(
            geographical_entity=entity
        )
        items = self.validated_data
        for old in old_data:
            exists = (
                [item for item in items if
                    old.id == item.validated_data['id']]
            )
            if len(exists) == 0:
                old.delete()
        results = []
        for item in items:
            obj = item.save(entity)
            results.append(obj)
        return results


class EntityCodeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    code_id = serializers.IntegerField()

    def validate_code(self, value):
        stripped_value = value.strip() if value else ''
        return stripped_value

    def validate_default(self, value):
        if 'default_set' in self.context:
            if value is True and value in self.context['default_set']:
                raise serializers.ValidationError(
                    'Duplicate default'
                )
        return value

    def save(self, entity):
        code_id = self.validated_data['id']
        code_type = self.validated_data['code_id']
        code_value = self.validated_data['value']
        default = self.validated_data['default']
        if code_id > 0:
            try:
                entity_code = EntityId.objects.get(
                    geographical_entity=entity, id=code_id
                )
                entity_code.value = code_value
                entity_code.save()
            except EntityId.DoesNotExist:
                pass
        else:
            entity_code = EntityId.objects.create(
                value=code_value,
                default=default,
                geographical_entity=entity,
                code_id=code_type
            )
        return entity_code

    class Meta:
        model = EntityId
        list_serializer_class = EntityCodeListSerializer
        fields = [
            'id', 'default', 'value', 'code_id'
        ]


class EntityEditSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    codes = serializers.SerializerMethodField(
        source=EntityCodeSerializer(many=True)
    )
    names = serializers.SerializerMethodField(
        source=EntityNameSerializer(many=True)
    )
    type = serializers.SerializerMethodField()

    def validate(self, data):
        data = super().validate(data)
        if 'codes' in self.context:
            name = EntityCodeSerializer(
                data=self.context['codes'],
                many=True
            )
            name.is_valid(raise_exception=True)
            data['codes'] = name
        if 'names' in self.context:
            name = EntityNameSerializer(
                data=self.context['names'],
                many=True
            )
            name.is_valid(raise_exception=True)
            data['names'] = name
        if 'type' in self.context:
            data['type'] = self.context['type']
        return data

    def validate_type(self, value):
        if not value:
            raise serializers.ValidationError(
                'Type cannot be NULL'
            )

    def get_names(self, obj):
        names = EntityName.objects.filter(
            geographical_entity=obj
        ).order_by('-default', 'name')
        return EntityNameSerializer(names, many=True).data

    def get_codes(self, obj):
        codes = EntityId.objects.filter(
            geographical_entity=obj
        ).order_by('-default', 'value')
        return EntityCodeSerializer(codes, many=True).data

    def get_type(self, obj):
        if obj.type:
            return obj.type.label
        return ''

    def save(self):
        entity_type, created = EntityType.objects.get_or_create(
            label=self.validated_data['type']
        )
        entity = GeographicalEntity.objects.get(id=self.validated_data['id'])
        entity.privacy_level = self.validated_data['privacy_level']
        entity.source = self.validated_data['source']
        entity.type = entity_type
        entity.save()
        if 'codes' in self.validated_data:
            self.validated_data['codes'].save(entity)
        if 'names' in self.validated_data:
            self.validated_data['names'].save(entity)
        entity.dataset.sync_status = (
            entity.dataset.DatasetSyncStatus.OUT_OF_SYNC
        )
        entity.dataset.save()

    class Meta:
        model = GeographicalEntity
        fields = [
            'id',
            'source',
            'type',
            'privacy_level',
            'names',
            'codes'
        ]
