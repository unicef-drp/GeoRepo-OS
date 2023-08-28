"""Custom token for API Key"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from knox.models import AuthToken


class ApiKey(models.Model):
    token = models.OneToOneField(
        AuthToken,
        on_delete=models.CASCADE,
        primary_key=True,
    )

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

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        verbose_name = _("API Key")
        verbose_name_plural = _("API Keys")

    def __str__(self):
        return f'API Key for {self.token.user.email}'
