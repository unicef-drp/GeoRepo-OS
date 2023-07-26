from azure_auth.backends import AzureAuthRequiredMixin
from django.views.generic import TemplateView
from django.conf import settings
from core.models.preferences import SitePreferences


class DashboardView(AzureAuthRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super(DashboardView, self).get_context_data(**kwargs)
        ctx['use_azure_auth'] = settings.USE_AZURE
        ctx['georepo_code_version'] = settings.CODE_RELEASE_VERSION
        ctx['help_base_url'] = (
            SitePreferences.preferences().base_url_help_page
        )
        return ctx
