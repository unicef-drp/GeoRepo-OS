"""Middleware class to check for valid Azure B2C Token."""
from django.shortcuts import redirect
from django.urls import reverse

from .configuration import AzureAuthConfig
from .handlers import AzureAuthHandler
from django.contrib.auth import logout


class AzureAuthMiddleware:
    """Middleware class to check for valid Azure B2C Token."""

    def __init__(self, get_response):
        """Initialize class with get_response function."""
        self.get_response = get_response

    def __call__(self, request):
        """Check whether there is valid token."""
        public_urls = [reverse(view_name) for
                       view_name in AzureAuthConfig.PUBLIC_URLS]
        if request.path_info in public_urls:
            return self.get_response(request)
        if AzureAuthHandler(request).get_token_from_cache():
            # If the user is authenticated
            if request.user.is_authenticated:
                return self.get_response(request)
        # if token auth is failed, then logout django session
        logout(request)
        # redirect to django login
        return redirect("login")
