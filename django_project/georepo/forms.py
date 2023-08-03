from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from azure_auth.backends import AzureAuthBackend

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
