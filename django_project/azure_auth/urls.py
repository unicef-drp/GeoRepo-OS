"""URL Patterns for Azure B2C authentication."""
from azure_auth.views import (
    azure_auth_callback,
    azure_auth_login,
    azure_auth_logout,
    azure_auth_redirect,
    azure_auth_third_party
)
from azure_auth.api_views import AzureRefreshToken
from django.urls import path


app_name = "azure_auth"
urlpatterns = [
    path("azure-auth/login", azure_auth_login, name="login"),
    path("azure-auth/logout", azure_auth_logout, name="logout"),
    path("signin-oidc", azure_auth_callback, name="callback"),
    path("redirect", azure_auth_redirect, name="redirect"),
    path("azure-auth/third-party", azure_auth_third_party, name="third-party"),
    path("azure-auth/token", AzureRefreshToken.as_view(), name="token"),
]
