from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from django.shortcuts import get_object_or_404
from georepo.models.module import Module
from georepo.utils.permission import (
    get_modules_to_add_dataset
)
from dashboard.api_views.common import IsSuperUser


class ModuleDashboard(AzureAuthRequiredMixin, APIView):
    """
    Returns list of modules
    """
    permission_classes = [IsSuperUser]

    def get(self, request, *args, **kwargs):
        modules = Module.objects.all()
        modules = get_modules_to_add_dataset(
            request.user,
            modules
        )
        module_data = []
        for module in modules:
            module_data.append({
                'id': module.id,
                'name': module.name,
                'description': module.description,
                'uuid': module.uuid,
                'is_active': module.is_active,
                'status': 'Active' if module.is_active else 'Inactive'
            })
        return Response(module_data)

    def post(self, request, *args, **kwargs):
        module_uuid = kwargs.get('uuid')
        module = get_object_or_404(
            Module,
            uuid=module_uuid
        )
        description = request.data.get('description')
        is_active = request.data.get('is_active')
        tmp_active = module.is_active
        module.is_active = is_active
        module.description = description
        if tmp_active and not module.is_active:
            # deactivate module
            module.deactivated_at = datetime.now()
            module.deactivated_by = request.user
        elif not tmp_active and module.is_active:
            # reactivate module
            module.deactivated_at = None
            module.deactivated_by = None
        module.save()
        return Response(status=204)
