"""Registered domain for azure authentication."""
from django.contrib.auth.models import Group
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class RegisteredDomain(models.Model):
    """Registered domain for azure authentication."""

    domain = models.CharField(max_length=256, unique=True)
    group = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL,
        help_text=_(
            'Autoassign user under the domain to the group.'
        )
    )
