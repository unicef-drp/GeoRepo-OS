"""URL Patterns for Azure B2C authentication."""
from azure_auth.views import (
    azure_auth_callback,
    azure_auth_login,
    azure_auth_logout,
    azure_auth_redirect,
)

from django.urls import path


app_name = "azure_auth"
urlpatterns = [
    path("azure-auth/login", azure_auth_login, name="login"),
    path("azure-auth/logout", azure_auth_logout, name="logout"),
    path("signin-oidc", azure_auth_callback, name="callback"),
    path("redirect", azure_auth_redirect, name="redirect"),
]


# azure_auth_urlpatterns = [
#     # path("", include("azure_auth.urls", namespace="azure_auth")),
#     path("auth/", include("azure_auth.urls", namespace="azure_auth")),
# ]

# azure_auth_urlpatterns += [
#     path("accounts/login/", azure_auth_login, name="sso_login"),
#     path("accounts/logout/", azure_auth_logout, name="sso_logout"),
# ]
