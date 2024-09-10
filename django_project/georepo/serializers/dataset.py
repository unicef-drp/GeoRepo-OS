from django.conf import settings
from django.db.models import Q
from django.urls.exceptions import NoReverseMatch
from rest_framework import serializers
from drf_yasg import openapi
from rest_framework.reverse import reverse
from georepo.serializers.common import APIResponseModelSerializer
from georepo.models import (
    Dataset,
    DatasetGroup,
    GeographicalEntity,
    DatasetAdminLevelName,
    BoundaryType,
    EntityType,
    EntityId
)


class DatasetItemSerializer(APIResponseModelSerializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Dataset',
            'properties': {
                'name': openapi.Schema(
                    title='Dataset Name',
                    type=openapi.TYPE_STRING
                ),
                'uuid': openapi.Schema(
                    title='Dataset UUID',
                    type=openapi.TYPE_STRING,
                ),
                'short_code': openapi.Schema(
                    title='Short Code',
                    type=openapi.TYPE_STRING,
                ),
                'type': openapi.Schema(
                    title='Module Name',
                    type=openapi.TYPE_STRING,
                ),
                'is_favorite': openapi.Schema(
                    title='Favorite Dataset',
                    type=openapi.TYPE_BOOLEAN,
                ),
                'last_update': openapi.Schema(
                    title='Dataset Last Updated Date Time',
                    type=openapi.TYPE_STRING,
                ),
            },
            'required': ['name', 'uuid', 'type'],
            'example': [{
                'name': 'World',
                'uuid': (
                    '2d8e9345-2ff8-41d3-9d16-65bd08ad5f3c'
                ),
                'short_code': 'TST',
                'type': 'Admin Boundaries',
                'is_favorite': False,
                'last_update': '2022-08-15T08:09:15.049806Z'
            }]
        }

        model = Dataset
        fields = [
            'name',
            'uuid',
            'short_code',
            'type',
            'is_favorite',
            'last_update'
        ]

    def get_name(self, obj: Dataset):
        return obj.label

    def get_is_favorite(self, obj: Dataset):
        return obj.is_preferred

    def get_type(self, obj: Dataset):
        return obj.module.name if obj.module else ''

    def get_last_update(self, obj: Dataset):
        if obj.last_update:
            return obj.last_update
        return ''


class DatasetGroupSerializer(serializers.ModelSerializer):
    dataset = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, obj: DatasetGroup):
        if obj.created_by:
            return (
                obj.created_by.first_name
                if obj.created_by.first_name
                else obj.created_by.username
            )

    def get_dataset(self, obj: DatasetGroup):
        return obj.name

    def get_date(self, obj: DatasetGroup):
        return obj.created_at

    class Meta:
        model = DatasetGroup
        fields = [
            'id', 'dataset', 'created_by', 'date'
        ]


class AdminLevelSerializer(APIResponseModelSerializer):
    level_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Level',
            'properties': {
                'level': openapi.Schema(
                    title='Admin Level',
                    type=openapi.TYPE_INTEGER
                ),
                'level_name': openapi.Schema(
                    title='Admin Level Name',
                    type=openapi.TYPE_STRING
                ),
                'url': openapi.Schema(
                    title=(
                        'API URL that returns GeoJson for '
                        'entities in this level'
                    ),
                    type=openapi.TYPE_STRING,
                )
            },
            'required': ['level', 'level_name', 'url'],
            'example': {
                'level': 0,
                'level_name': 'Country',
                'url': (
                    '{BASE_URL}/api/v1/search/dataset/'
                    '4078cbf8-f773-4bd8-9450-5685d86f8b27/'
                    'entity/level/0/'
                )
            }
        }

        model = DatasetAdminLevelName
        fields = [
            'level',
            'level_name',
            'url'
        ]

    def get_level_name(self, obj: DatasetAdminLevelName):
        return obj.label if obj.label else ''

    def get_url(self, obj: DatasetAdminLevelName):
        url = None
        if 'request' in self.context and 'uuid' in self.context:
            uuid = self.context['uuid']
            request = self.context['request']
            try:
                url = reverse(
                    'search-entity-by-level',
                    kwargs={
                        'uuid': uuid,
                        'admin_level': obj.level
                    },
                    request=request
                )
                url = request.build_absolute_uri(url)
                if not settings.DEBUG:
                    # if not dev env, then replace with https
                    url = url.replace('http://', 'https://')
            except NoReverseMatch:
                pass
        return url


class DetailedDatasetSerializer(APIResponseModelSerializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    dataset_levels = serializers.SerializerMethodField()
    possible_id_types = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Dataset Detail',
            'properties': {
                'name': openapi.Schema(
                    title='Dataset Name',
                    type=openapi.TYPE_STRING
                ),
                'uuid': openapi.Schema(
                    title='Dataset UUID',
                    type=openapi.TYPE_STRING
                ),
                'short_code': openapi.Schema(
                    title='Dataset Short Code',
                    type=openapi.TYPE_STRING
                ),
                'type': openapi.Schema(
                    title='Module Name',
                    type=openapi.TYPE_STRING
                ),
                'is_favorite': openapi.Schema(
                    title='Favorite Dataset',
                    type=openapi.TYPE_BOOLEAN,
                ),
                'description': openapi.Schema(
                    title='Dataset Description',
                    type=openapi.TYPE_STRING
                ),
                'last_update': openapi.Schema(
                    title='Last Update Date Time',
                    type=openapi.TYPE_STRING
                ),
                'dataset_levels': openapi.Schema(
                    title='Admin levels in dataset',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties=(
                            AdminLevelSerializer.Meta.
                            swagger_schema_fields['properties']
                        )
                    )
                ),
                'possible_id_types': openapi.Schema(
                    title='Possible id types that are used in dataset',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_STRING
                    )
                ),
            },
            'required': [
                'name', 'uuid', 'type',
                'dataset_levels'
            ],
            'example': {
                'name': 'Ukraine',
                'uuid': '8c4582ab-15b1-4ed0-b8e4-00640ec10a65',
                'type': 'Admin Boundaries',
                'is_favorite': False,
                'description': 'Ukraine Boundaries',
                'last_update': '2023-01-26T03:39:01.518482Z',
                'dataset_levels': [
                    (
                        AdminLevelSerializer.Meta.
                        swagger_schema_fields['example']
                    )
                ],
                'possible_id_types': [
                    'ucode',
                    'concept_uuid',
                    'uuid',
                    'PCode'
                ]
            }
        }

        model = Dataset
        fields = [
            'name',
            'uuid',
            'short_code',
            'type',
            'is_favorite',
            'description',
            'last_update',
            'dataset_levels',
            'possible_id_types'
        ]

    def get_name(self, obj: Dataset):
        return obj.label

    def get_type(self, obj: Dataset):
        return obj.module.name if obj.module else ''

    def get_is_favorite(self, obj: Dataset):
        return obj.is_preferred

    def get_last_update(self, obj: Dataset):
        if obj.last_update:
            return obj.last_update
        return ''

    def get_dataset_levels(self, obj: Dataset):
        level_names = DatasetAdminLevelName.objects.filter(
            dataset=obj
        ).exclude(
            Q(label__isnull=True) | Q(label='')
        ).order_by('level').distinct('level')
        request = None
        if 'request' in self.context:
            request = self.context['request']
        return AdminLevelSerializer(
            level_names,
            context={
                'uuid': obj.uuid,
                'request': request
            },
            many=True
        ).data

    def get_possible_id_types(self, obj: Dataset):
        ids = EntityId.objects.filter(
            geographical_entity__dataset__id=obj.id,
            geographical_entity__is_approved=True
        ).order_by('code__name').values_list(
            'code__name', flat=True
        ).distinct('code__name')
        results = [
            'ucode',
            'uuid',
            'concept_uuid'
        ]
        results.extend(ids.all())
        return results


class DatasetAdminLevelNameListSerializer(serializers.ListSerializer):

    def validate(self, data):
        level_set = set()
        results = []
        for item in data:
            obj = DatasetAdminLevelNameSerializer(
                data=item,
                context={
                    'level_set': level_set,
                    'user': (
                        self.context['user'] if
                        'user' in self.context else None
                    )
                }
            )
            obj.is_valid(raise_exception=True)
            level_set.add(obj.validated_data['level'])
            results.append(obj)
        return results

    def save(self, dataset):
        old_data = DatasetAdminLevelName.objects.filter(
            dataset=dataset
        ).order_by('level')
        items = self.validated_data
        for old in old_data:
            exists = (
                [item for item in items if
                    old.level == item.validated_data['level']]
            )
            if len(exists) == 0:
                old.delete()
        results = []
        for item in items:
            obj = item.save(dataset)
            results.append(obj)
        return results


class DatasetAdminLevelNameSerializer(serializers.ModelSerializer):

    def validate_label(self, value):
        stripped_value = value.strip() if value else ''
        return stripped_value

    def validate_level(self, value):
        if value < 0:
            raise serializers.ValidationError(
                f'Invalid admin level {value}'
            )
        if 'level_set' in self.context and value in self.context['level_set']:
            raise serializers.ValidationError(
                f'Duplicate admin level {value}'
            )
        return value

    def save(self, dataset):
        label = self.validated_data['label']
        level = self.validated_data['level']
        adm_levelname, _ = DatasetAdminLevelName.objects.update_or_create(
            dataset=dataset,
            level=level,
            defaults={
                'label': label,
                'created_by': (
                    self.context['user'] if 'user' in self.context else None
                )
            }
        )
        return adm_levelname

    class Meta:
        model = DatasetAdminLevelName
        list_serializer_class = DatasetAdminLevelNameListSerializer
        fields = [
            'label', 'level'
        ]


class DatasetBoundaryTypeListSerializer(serializers.ListSerializer):

    def validate(self, data):
        value_set = set()
        results = []
        for item in self.initial_data:
            existing_id = None
            try:
                if 'id' in item:
                    existing_id = int(item['id'])
            except ValueError:
                pass
            if existing_id:
                instance = BoundaryType.objects.get(id=existing_id)
                obj = DatasetBoundaryTypeSerializer(
                    instance,
                    data=item,
                    context={
                        'value_set': value_set
                    }
                )
            else:
                obj = DatasetBoundaryTypeSerializer(
                    data=item,
                    context={
                        'value_set': value_set
                    }
                )
            obj.is_valid(raise_exception=True)
            results.append(obj)
            value_set.add(obj.validated_data['value'])
        return results

    def save(self, dataset):
        old_data = BoundaryType.objects.filter(
            dataset=dataset
        ).order_by('id')
        items = self.validated_data
        for old in old_data:
            exists = (
                [item for item in items if
                    item.instance and old.id == item.instance.id]
            )
            if len(exists) == 0:
                old.type.delete()
        results = []
        for item in items:
            obj = item.save(dataset=dataset)
            results.append(obj)
        return results


class DatasetBoundaryTypeSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='type.label')
    type_id = serializers.SerializerMethodField()
    total_entities = serializers.SerializerMethodField()

    def get_type_id(self, obj: BoundaryType):
        return obj.type.id if obj.type else None

    def get_total_entities(self, obj: BoundaryType):
        return GeographicalEntity.objects.filter(
            type=obj.type
        ).count()

    def validate_label(self, value):
        stripped_value = value.strip() if value else ''
        if stripped_value == '':
            raise serializers.ValidationError(
                'Label cannot be empty!'
            )
        return stripped_value

    def validate_value(self, value):
        stripped_value = value.strip() if value else ''
        if stripped_value == '':
            raise serializers.ValidationError(
                'Value cannot be empty!'
            )
        if (
            'value_set' in self.context and
            stripped_value in self.context['value_set']
        ):
            raise serializers.ValidationError(
                f'Duplicate value {stripped_value}'
            )
        return stripped_value

    def create(self, validated_data):
        label = validated_data['type']['label']
        value = validated_data['value']
        # create new entity type
        entity_type = EntityType.objects.get_by_label(
            label
        )
        obj = BoundaryType.objects.create(
            type=entity_type,
            value=value,
            dataset=validated_data['dataset']
        )
        return obj

    def update(self, instance, validated_data):
        label = validated_data['type']['label']
        value = validated_data.get('value', instance.value)
        # create or update the entity type
        instance.type.label = label
        instance.type.save()
        instance.value = value
        instance.save()
        return instance

    class Meta:
        model = BoundaryType
        list_serializer_class = DatasetBoundaryTypeListSerializer
        fields = [
            'id',
            'label',
            'type_id',
            'value',
            'total_entities'
        ]
