"""Views for Azure B2C Authentication."""
import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import resolve_url, render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect

from .handlers import AzureAuthHandler
from .exceptions import InvalidUserError
from .models import ThirdPartyApplication

logger = logging.getLogger(__name__)


def azure_auth_login(request):
    """Redirect user to Azure B2C authentication page."""
    return HttpResponseRedirect(AzureAuthHandler(request).get_auth_uri())


def azure_auth_logout(request):
    """Redirect user to Azure B2C logout page."""
    logout(request)
    return HttpResponseRedirect(AzureAuthHandler(request).get_logout_uri())


def azure_auth_callback(request):
    """Callback/Reply URL that is called from code grant flow."""
    handler = AzureAuthHandler(request)
    login_path = request.build_absolute_uri(
        resolve_url(settings.USER_NO_ACCESS_URL or settings.LOGIN_URL)
    ) + '?no_access=true'
    output = HttpResponseRedirect(
        handler.get_logout_uri(login_path)
    )
    try:
        token = handler.get_token_from_flow()
        user = authenticate(request, token=token)
        if user:
            login(request, user)
            next_uri = handler.get_auth_flow_next_uri()
            redirect_uri = next_uri or settings.LOGIN_REDIRECT_URL
            output = HttpResponseRedirect(redirect_uri)
    except InvalidUserError as e:
        # thrown when non-unicef user does not exist yet
        logger.exception(e)
    except Exception as e:
        logger.exception(e)
    logger.debug("_azure_auth_callback: %s", output)
    return output


def azure_auth_redirect(request):
    """azure_auth_redirect to handle Django success/error messages."""
    output = HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    try:
        token = AzureAuthHandler(request).get_token_from_flow()
        user = authenticate(request, token=token)
        if user:
            login(request, user)
    except Exception as e:
        logger.exception(e)
    logger.debug("azure_auth_redirect: %s", output)
    return output


def azure_auth_third_party(request):
    client_id = request.GET.get('client_id')
    # fetch client registered origin
    app = get_object_or_404(
        ThirdPartyApplication,
        client_id=client_id
    )
    # fetch access token and refresh token from session
    token = AzureAuthHandler(request).get_token_from_cache()
    if token and 'access_token' in token:
        # store client_id to current user session
        third_party_client_key = 'third_party_granted_access'
        granted_client_ids = request.session.get(third_party_client_key, [])
        if client_id not in granted_client_ids:
            granted_client_ids.append(client_id)
        request.session[third_party_client_key] = granted_client_ids
        return render(request, 'third_party.html', context={
            'access_token': token['access_token'],
            'requester': app.origin,
            'session': request.session.session_key
        })
    url_redirect = (
        reverse('login') + '?next=' +
        request.path + '?' + request.GET.urlencode())
    return HttpResponseRedirect(url_redirect)
