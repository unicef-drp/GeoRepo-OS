"""Azure auth admin."""
from django.contrib import admin
from django.urls import reverse
from django.contrib.sites.models import Site
from azure_auth.models import RegisteredDomain, ThirdPartyApplication


class RegisteredDomainAdmin(admin.ModelAdmin):
    """RegisteredDomain admin."""

    list_display = ('domain', 'group')
    list_editable = ('group',)


class ThirdPartyApplicationAdmin(admin.ModelAdmin):
    """ThirdPartyApplication admin."""

    list_display = ('name', 'origin', 'client_id', 'auth_url')

    def auth_url(self, obj: ThirdPartyApplication):
        current_site = Site.objects.get_current()
        scheme = 'https://'
        url = reverse('azure_auth:third-party')
        return f'{scheme}{current_site.domain}{url}?client_id={obj.client_id}'

admin.site.register(RegisteredDomain, RegisteredDomainAdmin)
admin.site.register(ThirdPartyApplication, ThirdPartyApplicationAdmin)
