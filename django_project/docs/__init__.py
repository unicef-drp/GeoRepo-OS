from django.apps import AppConfig


class Config(AppConfig):
    """Documentation app."""

    name = 'docs'
    verbose_name = "Documentation center"


default_app_config = 'docs.Config'
