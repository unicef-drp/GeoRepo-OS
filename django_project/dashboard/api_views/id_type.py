from datetime import datetime
import re

from django.http import (
    HttpResponseBadRequest
)
from azure_auth.backends import AzureAuthRequiredMixin
from rest_framework.response import Response
from rest_framework.views import APIView

from georepo.models import (
    IdType
)

from dashboard.serializers.id_type import (
    IdTypeSerializer
)


class IdTypeList(AzureAuthRequiredMixin, APIView):
    """
    Get List of IdType
    """

    def get(self, request, format=None):
        id_types = IdType.objects.all().order_by('name')
        serializer = IdTypeSerializer(id_types, many=True)
        return Response(serializer.data)


class AddIdType(AzureAuthRequiredMixin, APIView):
    """
    Save new IdType
    Returns 400 if name exists
    """

    def post(self, request, format=None):
        req_name = request.data.get('name', '').strip()
        # ensure name contains allowed characters
        pattern = re.compile(r'^[\w-]+$')
        if not pattern.match(req_name):
            return HttpResponseBadRequest('Invalid name!')
        check_exist = IdType.objects.filter(
            name=req_name
        ).exists()
        if check_exist:
            return HttpResponseBadRequest('Name already exists!')
        id_type = IdType.objects.create(
            name=req_name,
            created_by=self.request.user,
            created_at=datetime.now
        )
        return Response(status=200, data=IdTypeSerializer(
            id_type
        ).data)
