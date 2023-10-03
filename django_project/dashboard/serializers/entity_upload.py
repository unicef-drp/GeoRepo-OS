from rest_framework import serializers

from dashboard.models import (
    EntityUploadStatus,
    APPROVED,
    REJECTED,
    PROCESSING_APPROVAL
)


class EntityUploadSerializer(serializers.ModelSerializer):
    level_0_entity = serializers.SerializerMethodField()
    upload = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    revision = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    is_comparison_ready = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_level_0_entity(self, obj: EntityUploadStatus):
        if obj.revised_geographical_entity:
            return obj.revised_geographical_entity.label
        # return module name
        dataset = obj.upload_session.dataset
        return dataset.module.name

    def get_upload(self, obj: EntityUploadStatus):
        return obj.upload_session_id

    def get_dataset(self, obj: EntityUploadStatus):
        return obj.upload_session.dataset.label

    def get_start_date(self, obj: EntityUploadStatus):
        return obj.upload_session.started_at

    def get_revision(self, obj: EntityUploadStatus):
        if obj.revised_geographical_entity:
            return obj.revised_geographical_entity.revision_number
        return obj.revision_number

    def get_submitted_by(self, obj: EntityUploadStatus):
        return obj.upload_session.uploader.username

    def get_module(self, obj: EntityUploadStatus):
        # return module name
        dataset = obj.upload_session.dataset
        return dataset.module.name

    def get_is_comparison_ready(self, obj: EntityUploadStatus):
        return True if obj.comparison_data_ready else False

    def get_status(self, obj: EntityUploadStatus):
        if obj.status == APPROVED:
            return APPROVED
        elif obj.status == REJECTED:
            return REJECTED
        elif obj.status == PROCESSING_APPROVAL:
            return APPROVED
        elif not self.get_is_comparison_ready(obj):
            return 'Processing'
        return 'Ready for Review'

    class Meta:
        model = EntityUploadStatus
        fields = [
            'id',
            'level_0_entity',
            'upload',
            'dataset',
            'start_date',
            'revision',
            'status',
            'submitted_by',
            'module',
            'is_comparison_ready',
        ]
