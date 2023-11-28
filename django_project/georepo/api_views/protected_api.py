from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from guardian.core import ObjectPermissionChecker

from georepo.auth import CustomTokenAuthentication
from georepo.models import Dataset, DatasetView, DatasetViewResource
from georepo.utils.permission import (
    get_view_permission_privacy_level
)


class IsDatasetAllowedAPI(APIView):
    if settings.USE_AZURE:
        from azure_auth.backends import JWTAccessTokenAuthentication
        authentication_classes = [
            CustomTokenAuthentication,
            JWTAccessTokenAuthentication
        ]
    else:
        authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]
    jwks_client = None

    def has_perm(self, user, privacy_level: int,
                 dataset: Dataset, dataset_view: DatasetView) -> bool:
        if user.is_superuser:
            return True
        obj_checker = ObjectPermissionChecker(user)
        obj_checker.prefetch_perms([dataset])
        obj_checker.prefetch_perms([dataset_view])
        max_privacy_level = get_view_permission_privacy_level(
            user,
            dataset,
            dataset_view=dataset_view
        )
        return privacy_level <= max_privacy_level

    def post(self, request, *args, **kwargs):
        request_url = request.query_params.get('request_url', '')
        try:
            params = list(filter(None, request_url.split('/')))
            resource_uuid = params[1]
            cache_key = (
                f'{resource_uuid}'
                f'{request.query_params.get("token", "")}'
            )
            allowed = cache.get(cache_key)
            if allowed is not None:
                if allowed:
                    return HttpResponse('OK')
                else:
                    return HttpResponseForbidden()
            view_resource = DatasetViewResource.objects.select_related(
                'dataset_view',
                'dataset_view__dataset',
                'dataset_view__dataset__module'
            ).get(
                uuid=resource_uuid
            )
            privacy_level = view_resource.privacy_level
            dataset = view_resource.dataset_view.dataset
            if not dataset.module.is_active:
                return Response(status=404, data='Not found.')
            redis_time_cache = 3600  # seconds
            allowed = (
                self.has_perm(self.request.user,
                              privacy_level,
                              dataset,
                              view_resource.dataset_view)
            )
            cache.set(cache_key, allowed, redis_time_cache)
            if not allowed:
                return HttpResponseForbidden()
        except (IndexError, DatasetViewResource.DoesNotExist):
            return HttpResponseForbidden()
        return HttpResponse('OK')
