import re
from django.conf import settings
from rest_framework import serializers
from taggit.serializers import (
    TagListSerializerField,
    TaggitSerializer)
from georepo.models import DatasetView, DatasetViewResource
from django.db import connection
from dashboard.models.entities_user_config import EntitiesUserConfig
from georepo.utils.permission import (
    PermissionType,
    get_external_view_permission_privacy_level
)
from georepo.utils.dataset_view import (
    get_view_tiling_status,
    get_view_product_status
)
from rest_framework.authtoken.models import Token


class DatasetViewSerializer(TaggitSerializer, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()
    mode = serializers.SerializerMethodField()
    layer_tiles = serializers.SerializerMethodField()
    tags = TagListSerializerField()
    permissions = serializers.SerializerMethodField()
    min_privacy = serializers.SerializerMethodField()
    max_privacy = serializers.SerializerMethodField()

    def get_mode(self, obj: DatasetView):
        if obj.is_static is None:
            return ''
        return 'Static' if obj.is_static else 'Dynamic'

    def get_dataset(self, obj: DatasetView):
        return obj.dataset.label if obj.dataset else '-'

    def get_is_default(self, obj: DatasetView):
        return 'Yes' if obj.default_type else 'No'

    def get_min_privacy(self, obj: DatasetView):
        return obj.min_privacy_level

    def get_max_privacy(self, obj: DatasetView):
        return obj.max_privacy_level

    def get_status(self, obj: DatasetView):
        tiling_status, _ = get_view_tiling_status(
            DatasetViewResource.objects.filter(
                dataset_view=obj
            )
        )
        return tiling_status

    def get_layer_tiles(self, obj: DatasetView):
        user = self.context.get('user', None)
        token = ''
        if user and Token.objects.filter(user=user).exists():
            token = str(user.auth_token)
        user_privacy_levels = self.context.get('user_privacy_levels', {})
        privacy_level = user_privacy_levels.get(obj.dataset.id, 0)
        if privacy_level == 0:
            # could be from external view
            privacy_level = (
                get_external_view_permission_privacy_level(user, obj)
            )
        if privacy_level > 0:
            resource = DatasetViewResource.objects.filter(
                dataset_view=obj,
                privacy_level=privacy_level
            ).first()
            if resource:
                updated_at = (
                    int(resource.vector_tiles_updated_at.timestamp())
                )
                return (
                    f'{settings.LAYER_TILES_BASE_URL}'
                    f'/layer_tiles/{str(resource.uuid)}/{{z}}/{{x}}/{{y}}'
                    f'?t={updated_at}&'
                    f'token={token}'
                )
        return '-'

    def get_permissions(self, obj: DatasetView):
        user = self.context['user']
        return PermissionType.get_permissions_for_datasetview(obj, user)

    class Meta:
        model = DatasetView
        fields = [
            'id',
            'name',
            'description',
            'tags',
            'mode',
            'dataset',
            'is_default',
            'min_privacy',
            'max_privacy',
            'layer_tiles',
            'status',
            'uuid',
            'permissions'
        ]


class DatasetViewDetailSerializer(TaggitSerializer,
                                  serializers.ModelSerializer):
    mode = serializers.SerializerMethodField()
    tags = TagListSerializerField()
    total = serializers.SerializerMethodField()
    preview_session = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    is_read_only = serializers.SerializerMethodField()
    dataset_uuid = serializers.SerializerMethodField()
    dataset_style_source_name = serializers.SerializerMethodField()
    query_string = serializers.SerializerMethodField()
    dataset_name = serializers.SerializerMethodField()
    module_name = serializers.SerializerMethodField()

    def get_mode(self, obj: DatasetView):
        if obj.is_static is None:
            return ''
        return 'static' if obj.is_static else 'dynamic'

    def get_total(self, obj: DatasetView):
        cursor = connection.cursor()
        total_count = 0
        try:
            clean_query = obj.query_string.replace(';', '')
            sql = f'SELECT COUNT(*) FROM ({clean_query}) AS custom_view'
            cursor.execute(sql)
            total_count = cursor.fetchone()[0]
            cursor.close()
        except Exception as ex: # noqa
            print(ex)
        return total_count

    def get_preview_session(self, obj: DatasetView):
        config = EntitiesUserConfig.objects.filter(
            dataset=obj.dataset,
            user=self.context['user'],
            query_string=obj.query_string
        ).last()
        if config is None:
            config = EntitiesUserConfig.objects.create(
                dataset=obj.dataset,
                user=self.context['user'],
                query_string=obj.query_string
            )
        return str(config.uuid)

    def get_permissions(self, obj: DatasetView):
        user = self.context['user']
        return PermissionType.get_permissions_for_datasetview(obj, user)

    def get_is_read_only(self, obj: DatasetView):
        return not obj.dataset.is_active

    def get_dataset_uuid(self, obj: DatasetView):
        return str(obj.dataset.uuid)

    def get_dataset_style_source_name(self, obj: DatasetView):
        if obj.dataset.style_source_name:
            return obj.dataset.style_source_name
        return str(obj.dataset.uuid)

    def get_query_string(self, obj: DatasetView):
        # remove dataset_id from original query_string
        query = obj.query_string if obj.query_string else ''
        # dataset_id after where
        pattern = r'dataset_id=[\d]+'
        query = re.sub(pattern, ' ', query, flags=re.IGNORECASE)
        pattern_1 = r'where[ ]+and'
        query = re.sub(pattern_1, 'where ', query, flags=re.IGNORECASE)
        pattern_2 = r'and[ ]+and'
        query = re.sub(pattern_2, 'and', query, flags=re.IGNORECASE)
        pattern_3 = r'[ ]+and[ ]+;'
        query = re.sub(pattern_3, ';', query, flags=re.IGNORECASE)
        # remove double or more spaces
        query = re.sub(' +', ' ', query)
        return query

    def get_dataset_name(self, obj: DatasetView):
        return obj.dataset.label

    def get_module_name(self, obj: DatasetView):
        return obj.dataset.module.name

    class Meta:
        model = DatasetView
        fields = [
            'id',
            'name',
            'description',
            'dataset',
            'mode',
            'status',
            'query_string',
            'mode',
            'tags',
            'total',
            'uuid',
            'preview_session',
            'permissions',
            'is_read_only',
            'dataset_uuid',
            'dataset_style_source_name',
            'dataset_name',
            'module_name'
        ]


class DatasetViewSyncSerializer(serializers.ModelSerializer):

    vector_tile_sync_progress = serializers.SerializerMethodField()
    product_sync_progress = serializers.SerializerMethodField()

    def get_vector_tile_sync_progress(self, obj):
        if obj.vector_tile_sync_status == obj.SyncStatus.OUT_OF_SYNC:
            return 0
        view_resources = DatasetViewResource.objects.filter(
            entity_count__gte=0
        )
        _, tiling_progress = get_view_tiling_status(view_resources)
        return tiling_progress

    def get_product_sync_progress(self, obj):
        if obj.product_sync_status == obj.SyncStatus.OUT_OF_SYNC:
            return 0
        view_resources = DatasetViewResource.objects.filter(
            entity_count__gte=0
        )
        _, product_progress = get_view_product_status(view_resources)
        return product_progress

    class Meta:
        model = DatasetView
        fields = [
            'id',
            'name',
            'is_tiling_config_match',
            'vector_tile_sync_status',
            'product_sync_status',
            'vector_tile_sync_progress',
            'product_sync_progress'
        ]


class DatasetViewResourceSyncSerializer(serializers.ModelSerializer):

    vector_tile_sync_progress = serializers.SerializerMethodField()
    geojson_sync_progress = serializers.SerializerMethodField()
    shapefile_sync_progress = serializers.SerializerMethodField()
    kml_sync_progress = serializers.SerializerMethodField()
    topojson_sync_progress = serializers.SerializerMethodField()

    def get_vector_tile_sync_progress(self, obj):
        if obj.vector_tile_sync_status == DatasetView.SyncStatus.OUT_OF_SYNC:
            return 0
        view_resources = DatasetViewResource.objects.filter(
            entity_count__gte=0
        )
        _, tiling_progress = get_view_tiling_status(view_resources)
        return tiling_progress

    def _get_product_progress(self, obj, product):
        if obj.product_sync_status == DatasetView.SyncStatus.OUT_OF_SYNC:
            return 0
        view_resources = DatasetViewResource.objects.filter(
            entity_count__gte=0
        )
        _, product_progress = get_view_product_status(
            view_resources,
            product=product
        )
        return product_progress

    def get_geojson_sync_progress(self, obj):
        return self._get_product_progress(obj, 'geojson')

    def get_shapefile_sync_progress(self, obj):
        return self._get_product_progress(obj, 'shapefile')

    def get_kml_sync_progress(self, obj):
        return self._get_product_progress(obj, 'kml')

    def get_topojson_sync_progress(self, obj):
        return self._get_product_progress(obj, 'topojson')

    class Meta:
        model = DatasetViewResource
        fields = [
            'id',
            'vector_tile_sync_status',
            'product_sync_status',
            'vector_tile_sync_progress',
            'geojson_sync_progress',
            'shapefile_sync_progress',
            'kml_sync_progress',
            'topojson_sync_progress'
        ]


class ViewSyncSerializer(serializers.Serializer):
    view_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    sync_options = serializers.ListField(child=serializers.CharField(), required=True)

    def validate_sync_options(self, attrs):
        options = set(attrs)
        accepted_options = {
            'tiling_config',
            'vector_tiles',
            'products'
        }
        if len(options - accepted_options) != 0:
            raise serializers.ValidationError(
                'Unknown actions'
            )
