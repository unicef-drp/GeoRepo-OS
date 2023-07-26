"""Azure auth admin."""
from django.contrib import admin

from azure_auth.models import RegisteredDomain


class RegisteredDomainAdmin(admin.ModelAdmin):
    """RegisteredDomain admin."""

    list_display = ('domain', 'group')
    list_editable = ('group',)


admin.site.register(RegisteredDomain, RegisteredDomainAdmin)
