import subprocess
from sentry_sdk import capture_message, configure_scope

from core.models import SitePreferences


def du(paths):
    """disk usage for each path"""
    cmd = ['du','-sc']
    cmd.extend(paths)
    bytes_arr = subprocess.check_output(cmd).splitlines()
    return [b.decode('utf-8') for b in bytes_arr]


class EphemeralMiddleware:
    """Add Ephemeral information after API call."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        pref = SitePreferences.preferences()
        if not pref.ephemeral_paths:
            return response

        resolver_match = getattr(request, 'resolver_match', None)
        possible_versions = []
        if resolver_match and resolver_match.namespace:
            possible_versions = resolver_match.namespace.split(':')

        # check for layer tiles path
        is_layer_tiles = '/layer_tiles/' in request.path
        if possible_versions or is_layer_tiles:
            with configure_scope() as scope:
                sizes = du(pref.ephemeral_paths)
                for size in sizes:
                    splits = size.split()
                    if len(splits) == 2:
                        scope.set_extra(splits[1], splits[0])
                capture_message('Ephemeral Storage Event')
        return response
