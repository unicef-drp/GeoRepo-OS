"""Core admin."""
from django.contrib import admin
from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils.html import format_html
from rest_framework.authtoken.models import TokenProxy
from knox.models import AuthToken
from rest_framework_tracking.admin import (
    APIRequestLogAdmin as BaseAPIRequestLogAdmin
)
from rest_framework_tracking.models import APIRequestLog as BaseAPIRequestLog
from core.models import (
    SitePreferences,
    SitePreferencesImage,
    ApiKey,
    APIRequestLog,
    CommandExecution
)
from core.tasks import execute_django_command

# Append code version to admin header
admin.site.site_header = (
    f'Django administration {settings.CODE_RELEASE_VERSION}'
)

# Unregister the default APIRequestLog admin
admin.site.unregister(BaseAPIRequestLog)


class SitePreferencesImageInline(admin.TabularInline):
    """SitePreferencesImageTheme inline."""

    model = SitePreferencesImage
    extra = 0


class SitePreferencesAdmin(admin.ModelAdmin):
    """Site Preferences admin."""

    fieldsets = (
        (None, {
            'fields': ('site_title',)
        }),
        ('Theme', {
            'fields': (
                'primary_color', 'anti_primary_color',
                'secondary_color', 'anti_secondary_color',
                'tertiary_color', 'anti_tertiary_color',
                'icon', 'favicon'
            ),
        }),
        ('Uploader Validation', {
            'fields': (
                'default_geometry_checker_params',
            )
        }),
        ('Boundary Matching', {
            'fields': (
                'geometry_similarity_threshold_new',
                'geometry_similarity_threshold_old'
            )
        }),
        ('Tile Configs Template', {
            'fields': (
                'tile_configs_template',
            )
        }),
        ('Dataset Short Code Exclusion', {
            'fields': (
                'short_code_exclusion',
            )
        }),
        ('Admin Level Names Template', {
            'fields': (
                'level_names_template',
            )
        }),
        ('API Configs', {
            'fields': (
                'api_config',
                'api_latest_version',
                'search_similarity',
                'search_simplify_tolerance'
            )
        }),
        ('Exporter Configs', {
            'fields': (
                'metadata_xml_config',
            )
        }),
        ('Permissions', {
            'fields': (
                'default_public_groups',
            )
        }),
        ('Maps', {
            'fields': (
                'maptiler_api_key',
            )
        }),
        ('Email', {
            'fields': (
                'default_admin_emails',
            )
        }),
        ('Swagger UI', {
            'fields': (
                'swagger_api_documentation_link',
            )
        }),
        ('Azure Blob Storage', {
            'fields': (
                'blob_storage_domain_whitelist',
            )
        }),
        ('Login Page', {
            'fields': (
                'login_help_text',
            )
        }),
        ('Logging', {
            'fields': (
                'ephemeral_paths', 'storage_checker_config',
            )
        }),
        ('Mapshaper', {
            'fields': (
                'mapshaper_config',
            )
        })
    )
    inlines = (SitePreferencesImageInline,)

    def has_add_permission(self, request, obj=None):
        # creation of API key is from FrontEnd
        return False


class APIKeyInline(admin.StackedInline):
    model = ApiKey


class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        'get_user', 'platform', 'owner', 'contact',
        'get_created', 'is_active', 'get_total_usage',
        'get_last_usage'
    )
    fields = ('platform', 'owner', 'contact', 'is_active')
    list_per_page = 20

    @admin.display(ordering='token__user__username', description='User')
    def get_user(self, obj):
        return obj.token.user

    @admin.display(ordering='token__created', description='Created')
    def get_created(self, obj):
        return obj.token.created

    def has_add_permission(self, request, obj=None):
        # creation of API key is from FrontEnd
        return False

    @admin.display(description='Total Usage')
    def get_total_usage(self, obj):
        return APIRequestLog.objects.filter(
            user=obj.token.user
        ).count()

    @admin.display(description='Last Usage')
    def get_last_usage(self, obj):
        last_log = APIRequestLog.objects.filter(
            user=obj.token.user
        ).order_by('-requested_at').first()
        return last_log.requested_at if last_log else None


class APIRequestLogAdmin(BaseAPIRequestLogAdmin):
    """Admin class for APIRequestLog model."""

    list_display = (
        "id",
        "requested_at",
        "response_ms",
        "status_code",
        "user",
        "view_method",
        "path"
    )
    list_filter = ("user", "status_code", "requested_at", "view_method")

    def changelist_view(self, request, extra_context=None):
        # Aggregate api logs per day
        chart_data = (
            APIRequestLog.objects.annotate(date=TruncDay("requested_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )

        extra_context = extra_context or {"chart_data": list(chart_data)}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

    def chart_data(self, start_date, end_date):
        return (
            APIRequestLog.objects.filter(
                requested_at__date__gte=start_date,
                requested_at__date__lte=end_date
            )
            .annotate(date=TruncDay("requested_at"))
            .values("date")
            .annotate(y=Count("id"))
            .order_by("-date")
        )


@admin.action(description='Duplicate selected command executions')
def duplicate_command_executions(modeladmin, request, queryset):
    """Duplicate command executions with execution state reset to pending.

    :param modeladmin: The current ModelAdmin instance.
    :type modeladmin: admin.ModelAdmin
    :param request: The current HTTP request.
    :type request: HttpRequest
    :param queryset: Selected CommandExecution queryset.
    :type queryset: QuerySet
    """
    for execution in queryset:
        CommandExecution.objects.create(
            command_name=execution.command_name,
            command_args=execution.command_args,
            command_kwargs=execution.command_kwargs,
            triggered_by=execution.triggered_by,
            status='pending',
        )
        modeladmin.message_user(
            request,
            (
                f'Duplicated "{execution.command_name}" as '
                'a new pending execution.'
            ),
            level='success',
        )


@admin.action(description='Re-run selected command executions')
def rerun_command_executions(modeladmin, request, queryset):
    """Re-run command executions by creating new execution records.

    :param modeladmin: The current ModelAdmin instance.
    :type modeladmin: admin.ModelAdmin
    :param request: The current HTTP request.
    :type request: HttpRequest
    :param queryset: Selected CommandExecution queryset.
    :type queryset: QuerySet
    """
    for execution in queryset:
        # Execute the command as background task
        execute_django_command.delay(execution_id=execution.id)

        modeladmin.message_user(
            request,
            (
                f'Command "{execution.command_name}" has been queued '
                f'for re-execution (New Execution ID: {execution.id})'
            ),
            level='success',
        )


class CommandExecutionAdmin(admin.ModelAdmin):
    """Admin class for CommandExecution model."""

    list_display = [
        'id',
        'command_name',
        'status_badge',
        'duration_display',
        'triggered_by',
        'started_at',
        'retry_count',
    ]
    list_filter = ['status', 'command_name', 'created_at']
    search_fields = ['command_name', 'celery_task_id', 'triggered_by']
    readonly_fields = [
        'celery_task_id',
        'created_at',
        'started_at',
        'completed_at',
        'duration_display',
        'stdout_display',
        'stderr_display',
    ]
    actions = [duplicate_command_executions, rerun_command_executions]

    fieldsets = (
        (
            'Command Details',
            {'fields': ('command_name', 'command_args', 'command_kwargs')},
        ),
        (
            'Execution Info',
            {
                'fields': (
                    'status',
                    'celery_task_id',
                    'triggered_by',
                    'retry_count',
                )
            },
        ),
        (
            'Timing',
            {
                'fields': (
                    'created_at',
                    'started_at',
                    'completed_at',
                    'duration_display',
                )
            },
        ),
        (
            'Output',
            {
                'fields': (
                    'stdout_display',
                    'stderr_display',
                    'error_message',
                ),
                'classes': ('collapse',),
            },
        ),
    )

    def status_badge(self, obj):
        """Return HTML badge for status."""
        colors = {
            'pending': 'gray',
            'running': 'blue',
            'success': 'green',
            'failed': 'red',
            'retrying': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = 'Status'

    def stdout_display(self, obj):
        """Return formatted standard output."""
        if not obj.stdout:
            return 'No output'
        return format_html('<pre>{}</pre>', obj.stdout)

    stdout_display.short_description = 'Standard Output'

    def stderr_display(self, obj):
        """Return formatted standard error."""
        if not obj.stderr:
            return 'No errors'
        return format_html('<pre style="color: red;">{}</pre>', obj.stderr)

    stderr_display.short_description = 'Standard Error'


admin.site.register(SitePreferences, SitePreferencesAdmin)
admin.site.unregister(TokenProxy)
admin.site.unregister(AuthToken)
admin.site.register(ApiKey, APIKeyAdmin)
admin.site.register(APIRequestLog, APIRequestLogAdmin)
admin.site.register(CommandExecution, CommandExecutionAdmin)
