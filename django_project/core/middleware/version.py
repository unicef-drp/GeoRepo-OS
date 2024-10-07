from django.conf import settings


class VersionMiddleware:
    """Add API Version and Code Version to response headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        resolver_match = getattr(request, 'resolver_match', None)
        possible_versions = []
        if resolver_match and resolver_match.namespace:
            possible_versions = resolver_match.namespace.split(':')
        if possible_versions:
            response['GeoRepo-API-Version'] = possible_versions[0]
        response['GeoRepo-Code-Version'] = settings.CODE_RELEASE_VERSION
        return response
