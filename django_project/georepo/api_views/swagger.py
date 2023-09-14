from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models.preferences import SitePreferences


class GetSwaggerApiDocLink(APIView, LimitOffsetPagination):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                'info': SitePreferences.
                preferences().
                swagger_api_documentation_link
            },
            200
        )
