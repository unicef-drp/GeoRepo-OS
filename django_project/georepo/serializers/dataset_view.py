import os
from drf_yasg import openapi
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.db.models.expressions import RawSQL
from django.db.models import Q
from django.conf import settings
from taggit.serializers import (
    TagListSerializerField,
    TaggitSerializer
)
from georepo.serializers.common import APIResponseModelSerializer
from georepo.models.entity import GeographicalEntity, EntityId
from georepo.models.dataset_view import DatasetView, DatasetViewResource
from georepo.models.dataset import DatasetAdminLevelName
from georepo.utils.dataset_view import generate_view_resource_bbox
from georepo.utils.permission import (
    get_view_permission_privacy_level
)


class DatasetViewItemSerializer(TaggitSerializer, APIResponseModelSerializer):
    root_entity = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()
    vector_tiles = serializers.SerializerMethodField()
    bbox = serializers.SerializerMethodField()
    tags = TagListSerializerField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'View',
            'properties': {
                'name': openapi.Schema(
                    title='View Name',
                    type=openapi.TYPE_STRING
                ),
                'uuid': openapi.Schema(
                    title='View UUID',
                    type=openapi.TYPE_STRING
                ),
                'description': openapi.Schema(
                    title='View Description',
                    type=openapi.TYPE_STRING
                ),
                'dataset': openapi.Schema(
                    title='Dataset Name',
                    type=openapi.TYPE_STRING
                ),
                'root_entity': openapi.Schema(
                    title=(
                        'The UCode of root_entity if '
                        'view contains only 1 root_entity'
                    ),
                    type=openapi.TYPE_STRING
                ),
                'last_update': openapi.Schema(
                    title='View Last Updated Date Time',
                    type=openapi.TYPE_STRING,
                ),
                'vector_tiles': openapi.Schema(
                    title='URL to view vector tile',
                    type=openapi.TYPE_STRING,
                ),
                'bbox': openapi.Schema(
                    title='Bounding Box of the view',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_NUMBER
                    )
                ),
                'tags': openapi.Schema(
                    title='Tag list',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_STRING
                    )
                ),
            },
            'example': {
                'name': 'World - Pakistan (Is Latest)',
                'description': (
                    'This dataset contains all the features '
                    'from main dataset'
                ),
                'dataset': 'World',
                'uuid': '21c8b48e-584d-4e76-b0d2-97db8208558f',
                'is_all_versions': False,
                'is_latest': False,
                'root_entity': 'PAK_V2',
                'last_update': '2022-08-15T08:09:15.049806Z',
                'vector_tiles': (
                    '{BASE_URL}/layer_tiles/'
                    '21c8b48e-584d-4e76-b0d2-97db8208558f'
                    '/{z}/{x}/{y}?t=1675079531'
                ),
                'bbox': [-121.5, 47.25, -120.4, 47.8],
                'tags': ['latest']
            }
        }
        model = DatasetView
        fields = [
            'name',
            'uuid',
            'description',
            'dataset',
            'root_entity',
            'last_update',
            'vector_tiles',
            'bbox',
            'tags'
        ]

    def vector_tile_url(self, resource: DatasetViewResource):
        url = None
        vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            str(resource.uuid)
        )
        # check path to vector tiles exist
        if os.path.exists(vector_tile_path) and 'request' in self.context:
            url = (
                f'/layer_tiles/{str(resource.uuid)}/{{z}}/{{x}}/{{y}}'
                f'?t={int(resource.vector_tiles_updated_at.timestamp())}'
            )
            request = self.context['request']
            url = request.build_absolute_uri(url)
            url = url.replace(
                '/%7Bz%7D/%7Bx%7D/%7By%7D',
                '/{z}/{x}/{y}'
            )
            if not settings.DEBUG:
                # if not dev env, then replace with https
                url = url.replace('http://', 'https://')
        return url

    def view_bbox(self, resource: DatasetViewResource):
        bbox = []
        if resource.bbox == '':
            _bbox = generate_view_resource_bbox(resource)
            bbox = _bbox.split(',') if _bbox else []
        else:
            bbox = resource.bbox.split(',')
        bbox = [float(b) for b in bbox]
        return bbox

    def get_dataset(self, obj: DatasetView):
        return obj.dataset.label

    def get_root_entity(self, obj: DatasetView):
        if obj.default_ancestor_code:
            entity = GeographicalEntity.objects.filter(
                dataset=obj.dataset,
                unique_code=obj.default_ancestor_code,
                is_approved=True
            ).order_by('revision_number').last()
            if entity and entity.unique_code:
                return entity.ucode
        return None

    def get_last_update(self, obj: DatasetView):
        if obj.last_update:
            return obj.last_update
        return ''

    def get_vector_tiles(self, obj: DatasetView):
        url = None
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return url
        user_privacy_level = self.context['user_privacy_level']
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return url
        url = self.vector_tile_url(resource)
        return url

    def get_bbox(self, obj: DatasetView):
        bbox = []
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return bbox
        user_privacy_level = self.context['user_privacy_level']
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return bbox
        bbox = self.view_bbox(resource)
        return bbox


class DatasetViewItemForUserSerializer(DatasetViewItemSerializer):

    def get_vector_tiles(self, obj: DatasetView):
        url = None
        obj_checker = self.context['obj_checker']
        user_privacy_level = get_view_permission_privacy_level(
            obj_checker, obj.dataset, obj
        )
        if user_privacy_level < obj.min_privacy_level:
            return url
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return url
        url = self.vector_tile_url(resource)
        return url

    def get_bbox(self, obj: DatasetView):
        bbox = []
        obj_checker = self.context['obj_checker']
        user_privacy_level = get_view_permission_privacy_level(
            obj_checker, obj.dataset, obj
        )
        if user_privacy_level < obj.min_privacy_level:
            return bbox
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return bbox
        bbox = self.view_bbox(resource)
        return bbox


class ViewAdminLevelSerializer(serializers.ModelSerializer):
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
                    '{BASE_URL}/api/v1/search/view/'
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
            url = reverse(
                'search-view-entity-by-level',
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
        return url


class ViewAdminLevelDictSerializer(serializers.Serializer):
    level = serializers.IntegerField()
    level_name = serializers.CharField(source='admin_level_name')
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        url = None
        if 'request' in self.context and 'uuid' in self.context:
            uuid = self.context['uuid']
            request = self.context['request']
            url = reverse(
                'search-view-entity-by-level',
                kwargs={
                    'uuid': uuid,
                    'admin_level': obj['level']
                },
                request=request
            )
            url = request.build_absolute_uri(url)
            if not settings.DEBUG:
                # if not dev env, then replace with https
                url = url.replace('http://', 'https://')
        return url


class DatasetViewDetailSerializer(TaggitSerializer,
                                  APIResponseModelSerializer):
    vector_tiles = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    last_update = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    tags = TagListSerializerField()
    dataset_levels = serializers.SerializerMethodField()
    possible_id_types = serializers.SerializerMethodField()
    bbox = serializers.SerializerMethodField()

    def get_vector_tiles(self, obj: DatasetView):
        url = None
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return url
        user_privacy_level = self.context['user_privacy_level']
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return url
        vector_tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            str(resource.uuid)
        )
        # check path to vector tiles exist
        if os.path.exists(vector_tile_path) and 'request' in self.context:
            url = (
                f'/layer_tiles/{str(resource.uuid)}/{{z}}/{{x}}/{{y}}'
                f'?t={int(resource.vector_tiles_updated_at.timestamp())}'
            )
            request = self.context['request']
            url = request.build_absolute_uri(url)
            url = url.replace(
                '/%7Bz%7D/%7Bx%7D/%7By%7D',
                '/{z}/{x}/{y}'
            )
            if not settings.DEBUG:
                # if not dev env, then replace with https
                url = url.replace('http://', 'https://')
        return url

    def get_name(self, obj: DatasetView):
        return obj.name

    def get_dataset(self, obj: DatasetView):
        return obj.dataset.label

    def get_last_update(self, obj: DatasetView):
        return obj.last_update

    def get_status(self, obj: DatasetView):
        if not obj.status:
            return ''
        statuses = dict(DatasetView.DatasetViewStatus.choices)
        return statuses[obj.status]

    def get_dataset_levels(self, obj: DatasetView):
        serializer = ViewAdminLevelSerializer
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return []
        user_privacy_level = self.context['user_privacy_level']
        entities = GeographicalEntity.objects.filter(
            dataset=obj.dataset,
            is_approved=True,
            privacy_level__lte=user_privacy_level
        ).exclude(
            Q(admin_level_name__isnull=True) | Q(admin_level_name='')
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(obj.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        if (
            obj.default_type and obj.default_ancestor_code and
            entities.exists()
        ):
            serializer = ViewAdminLevelDictSerializer
            level_names = entities.order_by(
                'level', 'admin_level_name'
            ).values(
                'level', 'admin_level_name'
            ).distinct('level', 'admin_level_name')
        else:
            level_names = DatasetAdminLevelName.objects.filter(
                dataset=obj.dataset
            ).exclude(
                Q(label__isnull=True) | Q(label='')
            ).order_by('level').distinct('level')
        request = None
        if 'request' in self.context:
            request = self.context['request']
        return serializer(
            level_names,
            context={
                'uuid': str(obj.uuid),
                'request': request
            },
            many=True
        ).data

    def get_possible_id_types(self, obj: DatasetView):
        results = [
            'ucode',
            'uuid',
            'concept_uuid'
        ]
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return results
        user_privacy_level = self.context['user_privacy_level']
        ids = EntityId.objects.filter(
            geographical_entity__dataset__id=obj.dataset.id,
            geographical_entity__is_approved=True,
            geographical_entity__privacy_level__lte=user_privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(obj.uuid))
        ids = ids.filter(
            geographical_entity__id__in=RawSQL(raw_sql, [])
        )
        ids = ids.order_by('code__name').values_list(
            'code__name', flat=True
        ).distinct('code__name')
        results.extend(ids.all())
        return results

    def get_bbox(self, obj: DatasetView):
        bbox = []
        # find the correct resource based on privacy level
        if 'user_privacy_level' not in self.context:
            return bbox
        user_privacy_level = self.context['user_privacy_level']
        resource = obj.datasetviewresource_set.filter(
            privacy_level=obj.get_resource_level_for_user(user_privacy_level)
        ).first()
        if resource is None:
            return bbox
        if resource.bbox == '':
            _bbox = generate_view_resource_bbox(resource)
            bbox = _bbox.split(',') if _bbox else []
        else:
            bbox = resource.bbox.split(',')
        bbox = [float(b) for b in bbox]
        return bbox

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Detail View',
            'properties': {
                'name': openapi.Schema(
                    title='View Name',
                    type=openapi.TYPE_STRING
                ),
                'description': openapi.Schema(
                    title='View Description',
                    type=openapi.TYPE_STRING
                ),
                'dataset': openapi.Schema(
                    title='Dataset Name',
                    type=openapi.TYPE_STRING
                ),
                'uuid': openapi.Schema(
                    title='View UUID',
                    type=openapi.TYPE_STRING,
                ),
                'created_at': openapi.Schema(
                    title='View Created Time',
                    type=openapi.TYPE_STRING,
                ),
                'last_update': openapi.Schema(
                    title='View Last Updated Date Time',
                    type=openapi.TYPE_STRING,
                ),
                'status': openapi.Schema(
                    title='View Status',
                    type=openapi.TYPE_STRING,
                ),
                'vector_tiles': openapi.Schema(
                    title='URL to view vector tile',
                    type=openapi.TYPE_STRING,
                ),
                'tags': openapi.Schema(
                    title='Tag list',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_STRING
                    )
                ),
                'dataset_levels': openapi.Schema(
                    title='Admin levels in dataset',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties=(
                            ViewAdminLevelSerializer.Meta.
                            swagger_schema_fields['properties']
                        )
                    )
                ),
                'possible_id_types': openapi.Schema(
                    title='Possible id types that are used in dataset view',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_STRING
                    )
                ),
                'bbox': openapi.Schema(
                    title='Bounding Box of the view',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_NUMBER
                    )
                ),
            },
            'required': ['uuid'],
            'example': {
                'name': 'World (Is Latest)',
                'description': (
                    'This dataset contains all the features '
                    'from main dataset'
                ),
                'dataset': 'World',
                'uuid': (
                    '2d8e9345-2ff8-41d3-9d16-65bd08ad5f3c'
                ),
                'last_update': '2022-08-15T08:09:15.049806Z',
                'tags': ['latest'],
                'dataset_levels': [
                    (
                        ViewAdminLevelSerializer.Meta.
                        swagger_schema_fields['example']
                    )
                ],
                'possible_id_types': [
                    'ucode',
                    'concept_uuid',
                    'uuid',
                    'PCode'
                ],
                'bbox': [-121.5, 47.25, -120.4, 47.8]
            }
        }
        model = DatasetView
        fields = [
            'name',
            'description',
            'dataset',
            'uuid',
            'created_at',
            'last_update',
            'status',
            'vector_tiles',
            'tags',
            'dataset_levels',
            'possible_id_types',
            'bbox'
        ]
