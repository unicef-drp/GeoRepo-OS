"""Core admin."""
from django.contrib import admin

from rest_framework.authtoken.models import TokenProxy
from rest_framework.authtoken.admin import TokenAdmin
from core.models import SitePreferences, SitePreferencesImage, CustomApiKey


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
                'api_latest_version'
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
        ('Help', {
            'fields': (
                'base_url_help_page',
            )
        }),
    )
    inlines = (SitePreferencesImageInline,)


class TokenDetailAdmin(TokenAdmin):
    list_display = ('key', 'user', 'platform', 'owner', 'contact', 'created')
    fields = ('user', 'platform', 'owner', 'contact')


admin.site.register(SitePreferences, SitePreferencesAdmin)
admin.site.unregister(TokenProxy)
admin.site.register(CustomApiKey, TokenDetailAdmin)
