from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class UploaderView(LoginRequiredMixin, TemplateView):
    template_name = 'uploader.html'
