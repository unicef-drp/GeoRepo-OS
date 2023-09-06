from django.contrib import admin

from docs.models import (
    Preferences, Block, Page, PageBlock, BlockChild
)


class PreferencesAdmin(admin.ModelAdmin):
    """Documentation preferences admin."""

    fieldsets = (
        (None, {
            'fields': ('documentation_base_url',)
        }),
    )


class PageBlockInline(admin.TabularInline):
    """PageBlock inline."""

    model = PageBlock
    extra = 1


class PageAdmin(admin.ModelAdmin):
    """Page admin."""

    list_display = ('name', 'relative_url')
    inlines = (PageBlockInline,)


class BlockChildInline(admin.TabularInline):
    """BlockChild inline."""

    fk_name = "parent"
    model = BlockChild
    extra = 1


class BlockAdmin(admin.ModelAdmin):
    """Block admin."""

    list_filter = ('url', 'anchor')
    inlines = (BlockChildInline,)


admin.site.register(Preferences, PreferencesAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Block, BlockAdmin)
