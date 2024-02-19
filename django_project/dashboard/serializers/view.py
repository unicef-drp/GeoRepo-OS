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
    get_view_tiling_status
)
from georepo.utils.directory_helper import (
    convert_size
)


def fetch_vector_tile_sync_status(obj: DatasetViewResource):
    if obj.status == DatasetView.DatasetViewStatus.ERROR:
        return 'Stopped'
    if (
        obj.vector_tile_sync_status ==
        DatasetViewResource.SyncStatus.SYNCING
    ):
        # task status may be empty when it is still in broker
        if obj.tiling_current_task and obj.tiling_current_task.status:
            return obj.tiling_current_task.status
    return obj.vector_tile_sync_status


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
    layer_preview = serializers.SerializerMethodField()

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
        statuses = dict(DatasetView.SyncStatus.choices)
        return statuses[tiling_status] if tiling_status in statuses else ''

    def get_layer_tiles(self, obj: DatasetView):
        user = self.context.get('user', None)
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
                privacy_level__lte=privacy_level,
                entity_count__gt=0
            ).first()
            if resource and resource.vector_tiles_size > 0:
                updated_at = (
                    int(resource.vector_tiles_updated_at.timestamp())
                )
                return (
                    f'{settings.LAYER_TILES_BASE_URL}'
                    f'/layer_tiles/{str(resource.uuid)}/{{z}}/{{x}}/{{y}}'
                    f'?t={updated_at}&'
                    'token={{YOUR_TOKEN}}&georepo_user_key={{YOUR_EMAIL}}'
                )
        return None

    def get_layer_preview(self, obj: DatasetView):
        user = self.context.get('user', None)
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
                privacy_level__lte=privacy_level,
                entity_count__gt=0
            ).first()
            if resource and resource.vector_tiles_size > 0:
                return f'/layer-test/?dataset_view_resource={str(resource.id)}'
        return None

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
            'permissions',
            'layer_preview'
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
        pattern = r'(gg\.)?dataset_id=[\d]+'
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

    dataset = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    simplification_status = serializers.SerializerMethodField()
    simplification_progress = serializers.SerializerMethodField()
    vector_tile_sync_status = serializers.SerializerMethodField()

    def get_dataset(self, obj):
        return obj.dataset_id

    def get_vector_tile_sync_progress(self, obj):
        if obj.vector_tile_sync_status == obj.SyncStatus.OUT_OF_SYNC:
            return 0
        view_resources = DatasetViewResource.objects.filter(
            dataset_view=obj,
            entity_count__gt=0
        )
        _, tiling_progress = get_view_tiling_status(view_resources)
        return tiling_progress

    def get_permissions(self, obj: DatasetView):
        user = self.context['user']
        return PermissionType.get_permissions_for_datasetview(obj, user)

    def get_simplification_status(self, obj: DatasetView):
        if obj.is_tiling_config_match:
            return obj.dataset.simplification_sync_status
        return obj.simplification_sync_status

    def get_simplification_progress(self, obj: DatasetView):
        if obj.is_tiling_config_match:
            return obj.dataset.simplification_progress_num
        return obj.simplification_progress_num

    def get_vector_tile_sync_status(self, obj: DatasetView):
        if obj.vector_tile_sync_status == DatasetView.SyncStatus.SYNCING:
            # check if all statuses are queued
            res_statuses = []
            for res in DatasetViewResource.objects.filter(
                dataset_view=obj,
                entity_count__gt=0
            ):
                status = fetch_vector_tile_sync_status(res)
                if status not in res_statuses:
                    res_statuses.append(status)
            if len(res_statuses) == 1 and 'Queued' in res_statuses:
                return 'Queued'
        return obj.vector_tile_sync_status

    class Meta:
        model = DatasetView
        fields = [
            'id',
            'dataset',
            'name',
            'is_tiling_config_match',
            'simplification_status',
            'vector_tile_sync_status',
            'centroid_sync_status',
            'simplification_progress',
            'vector_tiles_progress',
            'centroid_sync_progress',
            'permissions'
        ]


class DatasetViewResourceSyncSerializer(serializers.ModelSerializer):

    vector_tiles_size = serializers.SerializerMethodField()
    vector_tile_sync_status = serializers.SerializerMethodField()
    centroid_size = serializers.SerializerMethodField()
    centroid_sync_status = serializers.SerializerMethodField()

    def get_vector_tiles_size(self, obj: DatasetViewResource):
        return convert_size(obj.vector_tiles_size)

    def get_vector_tile_sync_status(self, obj: DatasetViewResource):
        return fetch_vector_tile_sync_status(obj)

    def get_centroid_sync_status(self, obj: DatasetViewResource):
        return obj.centroid_sync_status

    def get_centroid_size(self, obj: DatasetViewResource):
        total_size = 0
        for centroid_file in obj.centroid_files:
            total_size += (
                centroid_file['size'] if 'size' in centroid_file else 0
            )
        return convert_size(total_size)

    class Meta:
        model = DatasetViewResource
        fields = [
            'id',
            'uuid',
            'privacy_level',
            'vector_tile_sync_status',
            'vector_tiles_progress',
            'vector_tiles_size',
            'centroid_sync_status',
            'centroid_sync_progress',
            'centroid_size'
        ]


class ViewSyncSerializer(serializers.Serializer):
    view_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    sync_options = serializers.ListField(
        child=serializers.CharField(), required=True
    )

    def validate_sync_options(self, attrs):
        options = set(attrs)
        accepted_options = {
            'tiling_config',
            'vector_tiles',
            'simplify',
            'centroid'
        }
        if len(options - accepted_options) != 0:
            raise serializers.ValidationError(
                'Unknown actions'
            )
        return attrs
