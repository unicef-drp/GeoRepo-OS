"""Patch validation for auth model"""

from django.db.models.signals import class_prepared
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import gettext_lazy as _


def patch_username_validator_signal(sender, *args, **kwargs):
    """patch username validator"""
    if (sender.__name__ == "User" and
            sender.__module__ == "django.contrib.auth.models"):
        field = sender._meta.get_field("username")
        for v in field.validators:
            if isinstance(v, UnicodeUsernameValidator):
                v.regex = _lazy_re_compile(r'^[#\w.@+-]+\Z', 0)
                v.message = _(
                    'Required. 150 characters or fewer. '
                    'Letters, digits and @/./+/-/_/# only.'
                )
                v.flags = 0


class_prepared.connect(patch_username_validator_signal)
