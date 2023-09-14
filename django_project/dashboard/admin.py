import re
from datetime import datetime
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminFileWidget
from django.db.models.fields.files import FileField
from django import forms
from django.urls import path
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from tinymce.widgets import TinyMCE
from dashboard.models import (
    LayerFile,
    LayerUploadSession,
    EntityUploadStatus,
    LayerConfig,
    BoundaryComparison,
    Notification,
    Maintenance,
    BatchReview,
    STARTED,
    REVIEWING,
    EntitiesUserConfig
)
from georepo.models import TemporaryTilingConfig
from georepo.utils.layers import fetch_layer_file_metadata


class OverrideURLFileWidget(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        ori_output = super(OverrideURLFileWidget, self).render(
            name, value, attrs, renderer)
        result = re.sub(r"(.+)<a href=.+>(.+)<\/a>(.+)", r"\1 \2 \3",
                        ori_output)
        output = [result]
        return mark_safe(''.join(output))


@admin.action(description='Calculate Layer File Metadata')
def fetch_layer_file_metadata_action(modeladmin, request, queryset):
    for layer_file in queryset:
        fetch_layer_file_metadata(layer_file)


class LayerFileAdmin(admin.ModelAdmin):
    list_display = ('meta_id', 'name', 'upload_date', 'level', 'processed',
                    'feature_count', 'layer_type')
    formfield_overrides = {
        FileField: {'widget': OverrideURLFileWidget},
    }
    actions = [fetch_layer_file_metadata_action]


@admin.action(description='Validate entity upload')
def validate_entity_upload(modeladmin, request, queryset):
    from georepo.tasks import validate_ready_uploads
    for entity_upload in queryset:
        # revert status to STARTED
        entity_upload.status = STARTED
        entity_upload.comparison_data_ready = False
        entity_upload.boundary_comparison_summary = None
        entity_upload.progress = ''
        entity_upload.logs = ''
        entity_upload.started_at = datetime.now()
        entity_upload.summaries = None
        entity_upload.error_report = None
        entity_upload.save()
        task = validate_ready_uploads.apply_async(
            (entity_upload.id,),
            queue='validation'
        )
        entity_upload.task_id = task.id
        entity_upload.save(update_fields=['task_id'])


@admin.action(description='Run comparison boundary')
def run_comparison_boundary_action(modeladmin, request, queryset):
    from dashboard.tasks import run_comparison_boundary
    for entity_upload in queryset:
        entity_upload.status = REVIEWING
        entity_upload.save()
        run_comparison_boundary.apply_async(
            (entity_upload.id,),
            queue='validation'
        )


@admin.action(description='Load layer files to database')
def load_layer_files(modeladmin, request, queryset):
    from dashboard.tasks import process_layer_upload_session
    for upload_session in queryset:
        process_layer_upload_session.delay(upload_session.id)


class LayerUploadSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'status', 'started_at', 'modified_at')
    actions = [load_layer_files]


class EntityUploadAdmin(admin.ModelAdmin):
    search_fields = [
        'upload_session__source',
        'upload_session__dataset__label',
        'revised_entity_id',
        'revised_entity_name'
    ]
    actions = [validate_entity_upload, run_comparison_boundary_action]
    list_display = ('upload_session', 'get_dataset', 'started_at',
                    'status', 'get_entity',
                    'revised_entity_id', 'revised_entity_name',
                    'comparison_data_ready')
    raw_id_fields = (
        'original_geographical_entity',
        'revised_geographical_entity',
    )
    autocomplete_fields = (
        'original_geographical_entity',
        'revised_geographical_entity'
    )
    readonly_fields = ['started_at']
    formfield_overrides = {
        FileField: {'widget': OverrideURLFileWidget},
    }
    list_filter = ["status", "comparison_data_ready", "upload_session__dataset"]

    def get_dataset(self, obj):
        return obj.upload_session.dataset

    get_dataset.short_description = 'Dataset'
    get_dataset.admin_order_field = 'upload_session__dataset'

    def get_entity(self, obj):
        return (
            obj.revised_geographical_entity if
            obj.revised_geographical_entity else
            obj.original_geographical_entity
        )

    get_entity.short_description = 'Entity'
    get_dataset.admin_order_field = 'revised_geographical_entity'


class LayerConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level', 'created_by', 'created_at')


class BoundaryComparisonAdmin(admin.ModelAdmin):
    list_display = (
        'main_boundary',
        'comparison_boundary',
        'geometry_overlap_new'
    )
    raw_id_fields = (
        'main_boundary',
        'comparison_boundary'
    )


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'recipient', 'created_at')


class MaintenanceModelForm(forms.ModelForm):
    message = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    class Meta:
        model = Maintenance
        fields = ['message', 'scheduled_from_date',
                  'scheduled_end_date']


class MaintenanceAdmin(admin.ModelAdmin):
    change_list_template = "maintenance_changelist.html"
    form = MaintenanceModelForm
    list_display = ('id', 'scheduled_from_date',
                    'scheduled_end_date', 'created_by',
                    'created_at')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('goto_flower/', self.redirect_to_flower),
        ]
        return my_urls + urls

    def redirect_to_flower(self, request):
        return HttpResponseRedirect('/flower/')

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


class BatchReviewAdmin(admin.ModelAdmin):
    list_display = (
        'review_by',
        'is_approve',
        'status',
        'started_at',
        'finished_at',
        'progress'
    )


@admin.action(description='Clear old sessions')
def clear_old_sessions(modeladmin, request, queryset):
    from dashboard.tasks import clear_dashboard_dataset_session
    clear_dashboard_dataset_session.delay()
    modeladmin.message_user(
        request,
        'Old sessions have been cleared!',
        messages.SUCCESS
    )


class EntitiesUserConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'dataset', 'uuid',
                    'created_at', 'updated_at')
    actions = [clear_old_sessions]


class PrivacyLevelAdmin(admin.ModelAdmin):
    list_display = ('privacy_level', 'label')


class TemporaryTilingConfigAdmin(admin.ModelAdmin):
    list_display = ('session', 'zoom_level', 'level',
                    'simplify_tolerance', 'created_at')


admin.site.register(LayerFile, LayerFileAdmin)
admin.site.register(LayerUploadSession, LayerUploadSessionAdmin)
admin.site.register(EntityUploadStatus, EntityUploadAdmin)
admin.site.register(LayerConfig, LayerConfigAdmin)
admin.site.register(BoundaryComparison, BoundaryComparisonAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(Maintenance, MaintenanceAdmin)
admin.site.register(BatchReview, BatchReviewAdmin)
admin.site.register(EntitiesUserConfig, EntitiesUserConfigAdmin)
admin.site.register(TemporaryTilingConfig, TemporaryTilingConfigAdmin)
