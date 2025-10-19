from rest_framework import serializers
from georepo.models.export_request import (
    ExportRequestBase,
    ExportRequest,
    DatasetExportRequest
)


class ExportRequestBaseSerializer(serializers.ModelSerializer):

    job_uuid = serializers.UUIDField(source='uuid')
    requester = serializers.SerializerMethodField()
    date_requested = serializers.DateTimeField(source='submitted_on')
    date_completed = serializers.DateTimeField(source='finished_at')
    current_status = serializers.CharField(source='status_text')
    error_message = serializers.SerializerMethodField()
    simplification = serializers.SerializerMethodField()
    filter_summary = serializers.SerializerMethodField()
    download_expiry = serializers.SerializerMethodField()

    def get_requester(self, obj: ExportRequestBase):
        return obj.requester_name

    def get_simplification(self, obj: ExportRequestBase):
        if obj.is_simplified_entities:
            return obj.simplification_zoom_level
        return '-'

    def get_filter_summary(self, obj: ExportRequestBase):
        return [key.title() for key in obj.filters if
                key != 'points' and obj.filters[key]]

    def get_download_expiry(self, obj: ExportRequestBase):
        time_remaining = obj.download_time_remaining
        return time_remaining if time_remaining else '-'

    def get_error_message(self, obj: ExportRequestBase):
        return obj.errors if obj.errors else '-'

    class Meta:
        model = ExportRequestBase
        fields = [
            'id',
            'job_uuid',
            'format',
            'requester',
            'date_requested',
            'date_completed',
            'current_status',
            'status',
            'progress',
            'error_message',
            'simplification',
            'filter_summary',
            'download_link',
            'download_expiry'
        ]


class ExportRequestItemSerializer(ExportRequestBaseSerializer):

    class Meta:
        model = ExportRequest
        fields = ExportRequestBaseSerializer.Meta.fields


class DatasetExportRequestItemSerializer(ExportRequestBaseSerializer):

    class Meta:
        model = DatasetExportRequest
        fields = ExportRequestBaseSerializer.Meta.fields


class ExportRequestDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = ExportRequest
        fields = [
            'id',
            'uuid',
            'format',
            'requester_name',
            'submitted_on',
            'finished_at',
            'status',
            'status_text',
            'progress',
            'errors',
            'is_simplified_entities',
            'simplification_zoom_level',
            'filters',
            'download_link',
            'download_link_expired_on',
            'file_output_size',
            'download_time_remaining'
        ]


class DatasetExportRequestDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = DatasetExportRequest
        fields = [
            'id',
            'uuid',
            'format',
            'requester_name',
            'submitted_on',
            'finished_at',
            'status',
            'status_text',
            'progress',
            'errors',
            'is_simplified_entities',
            'simplification_zoom_level',
            'filters',
            'download_link',
            'download_link_expired_on',
            'file_output_size',
            'download_time_remaining'
        ]
