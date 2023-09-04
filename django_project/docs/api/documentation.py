from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from docs.models.page import Page
from docs.serializer.page import PageSerializer


class DocumentationDetail(APIView):
    """Documentation detail."""

    def get(self, request, page_name, *args, **kwargs):
        """Get access request detail."""
        page = get_object_or_404(Page, name=page_name)
        return Response(PageSerializer(page).data)
