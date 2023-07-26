"""Custom token for API Key"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token


class CustomApiKey(Token):
    """
    Additional detail to the token.

    Includes Proxy mapping pk to user pk for use in admin.
    """

    @property
    def pk(self):
        return self.user_id

    platform = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    owner = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    contact = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    class Meta:
        verbose_name = _("API Key")
        verbose_name_plural = _("API Keys")
