from rest_framework import serializers
from georepo.models import (
    Dataset, GeographicalEntity
)
from georepo.utils.permission import (
    PermissionType
)


class DatasetSerializer(serializers.ModelSerializer):
    dataset = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    source_name = serializers.SerializerMethodField()
    tiling_status = serializers.SerializerMethodField()
    sync_status = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    is_empty = serializers.SerializerMethodField()

    def get_type(self, obj: Dataset):
        if obj.module:
            return obj.module.name
        return ''

    class Meta:
        model = Dataset
        fields = [
            'id', 'dataset', 'created_by', 'type', 'date',
            'uuid', 'source_name',
            'geometry_similarity_threshold_new',
            'geometry_similarity_threshold_old',
            'tiling_status', 'sync_status', 'short_code',
            'generate_adm0_default_views',
            'max_privacy_level', 'min_privacy_level',
            'permissions', 'is_empty', 'is_active'
        ]

    def get_created_by(self, obj: Dataset):
        if obj.created_by:
            return (
                obj.created_by.first_name
                if obj.created_by.first_name
                else obj.created_by.username
            )
        return ''

    def get_dataset(self, obj: Dataset):
        return obj.label

    def get_date(self, obj: Dataset):
        if obj.created_at:
            return obj.created_at
        return ''

    def get_source_name(self, obj: Dataset):
        if obj.style_source_name:
            return obj.style_source_name
        return str(obj.uuid)

    def get_tiling_status(self, obj: Dataset):
        tiling_status = (
            Dataset.DatasetTilingStatus(obj.tiling_status).label
        )
        if obj.tiling_status == Dataset.DatasetTilingStatus.PROCESSING:
            tiling_status = f'{tiling_status} ({obj.tiling_progress:.0f}%)'
        return tiling_status

    def get_sync_status(self, obj: Dataset):
        return Dataset.SyncStatus(obj.sync_status).label

    def get_permissions(self, obj: Dataset):
        user = self.context['user']
        return PermissionType.get_permissions_for_dataset(obj, user)

    def get_is_empty(self, obj: Dataset):
        entity_count = GeographicalEntity.objects.filter(
            dataset=obj,
            is_approved=True
        ).count()
        return entity_count == 0
