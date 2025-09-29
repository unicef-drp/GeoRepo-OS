"""Core admin."""
from django.contrib import admin
from rest_framework.authtoken.models import TokenProxy
from knox.models import AuthToken
from rest_framework_tracking.admin import APIRequestLogAdmin
from rest_framework_tracking.models import APIRequestLog as BaseAPIRequestLog
from core.models import (
    SitePreferences,
    SitePreferencesImage,
    ApiKey,
    APIRequestLog
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
        })
    )
    inlines = (SitePreferencesImageInline,)

    def has_add_permission(self, request, obj=None):
        # creation of API key is from FrontEnd
        return False


class APIKeyInline(admin.StackedInline):
    model = ApiKey


class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('get_user', 'platform', 'owner', 'contact',
                    'get_created', 'is_active')
    fields = ('platform', 'owner', 'contact', 'is_active')

    @admin.display(ordering='token__user__username', description='User')
    def get_user(self, obj):
        return obj.token.user

    @admin.display(ordering='token__created', description='Created')
    def get_created(self, obj):
        return obj.token.created

    def has_add_permission(self, request, obj=None):
        # creation of API key is from FrontEnd
        return False


class APIRequestLogAdmin(APIRequestLogAdmin):
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
    search_fields = ("user", "path")


admin.site.register(SitePreferences, SitePreferencesAdmin)
admin.site.unregister(TokenProxy)
admin.site.unregister(AuthToken)
admin.site.register(ApiKey, APIKeyAdmin)
admin.site.register(APIRequestLog, APIRequestLogAdmin)
