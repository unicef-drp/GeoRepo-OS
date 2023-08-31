from datetime import datetime
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from azure_auth.backends import AzureAuthBackend
from core.models.preferences import SitePreferences
from georepo.models.dataset import Dataset
from georepo.utils.tile_configs import populate_tile_configs
from dashboard.tools.admin_level_names import (
    populate_default_dataset_admin_level_names
)
from georepo.utils.module_import import module_function

User = get_user_model()


class AzureAdminForm(forms.ModelForm):
    """Azure admin form."""

    def clean_email(self):
        """Check username."""
        email = AzureAuthBackend.clean_user_email(
            self.cleaned_data['email']
        )
        if User.objects.exclude(
                id=self.instance.id
        ).filter(email=email).count():
            raise ValidationError(
                "A user with this email already exists."
            )
        return email

    def save(self, commit=True):
        """Save user."""
        user = super().save(commit=False)
        if settings.USE_AZURE:
            user.username = user.email
            if commit:
                user.save()
        return user


class AzureAdminUserCreationForm(AzureAdminForm):
    """Azure Admin user create form."""

    class Meta:  # noqa D106
        model = User
        fields = ("email",)


class AzureAdminUserChangeForm(AzureAdminForm):
    """Azure Admin user change form."""

    class Meta:  # noqa D106
        model = User
        fields = '__all__'


class DatasetAdminForm(forms.ModelForm):
    """Dataset admin form."""

    def clean_short_code(self):
        """Check short_code."""
        short_code = self.cleaned_data['short_code']
        if Dataset.objects.exclude(
            id=self.instance.id
        ).filter(short_code=short_code).count():
            raise ValidationError(
                "A dataset with this short_code already exists."
            )
        exclusion = SitePreferences.preferences().short_code_exclusion
        if short_code != exclusion:
            # validate length must be 4
            if len(short_code) != 4:
                raise ValidationError(
                    "ShortCode must be 4 characters."
                )
        return short_code

    def save(self, commit=True):
        """Save dataset."""
        _tmp_active = self.instance.is_active
        _new = True if not self.instance.pk else False
        dataset = super(DatasetAdminForm, self).save(commit=commit)

        if _new:
            dataset.created_by = self.user
        else:
            if dataset.generate_adm0_default_views:
                generate_adm0 = module_function(
                    dataset.module.code_name,
                    'config',
                    'generate_adm0_default_views'
                )
                generate_adm0(dataset)
            if not dataset.is_active and _tmp_active:
                # deprecate dataset action
                dataset.deprecated_at = datetime.now()
                dataset.deprecated_by = self.user
            elif dataset.is_active and not _tmp_active:
                dataset.deprecated_at = None
                dataset.deprecated_by = None
        dataset.save()
        if _new:
            populate_tile_configs(dataset.id)
            populate_default_dataset_admin_level_names(dataset)
        return dataset


class DatasetAdminCreationForm(DatasetAdminForm):
    """Dataset admin create form."""

    class Meta:  # noqa D106
        model = Dataset
        fields = ('label', 'description', 'module', 'short_code',
                  'max_privacy_level', 'min_privacy_level',)


class DatasetAdminChangeForm(DatasetAdminForm):
    """Dataset admin change form."""

    def __init__(self, *args, **kwargs):
        super(DatasetAdminChangeForm, self).__init__(*args, **kwargs)
        self.fields['short_code'].disabled = True
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if not instance.short_code:
                self.fields['short_code'].disabled = False

    class Meta:  # noqa D106
        model = Dataset
        fields = '__all__'
