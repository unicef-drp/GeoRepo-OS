from typing import Tuple
from django.core.cache import cache
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response


class ApiCache(APIView, LimitOffsetPagination):
    permission_classes = [IsAuthenticated]
    cache_model = None
    use_cache = True

    def get_response_data(
                self, request,
                *args, **kwargs) -> Tuple[dict, dict | None]:
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        # disabled cache temporary
        # if self.use_cache and (
        #     request.GET.get('cached', 'True').lower()
        # ) == 'true':
        #     cached_data = self.get_cache()
        #     if cached_data:
        #         try:
        #             return Response(
        #                 cached_data['data'],
        #                 headers=cached_data['response_headers']
        #             )
        #         except (TypeError, KeyError):
        #             pass

        response_data, response_headers = self.get_response_data(
            request, *args, **kwargs
        )
        # disabled cache temporary
        # self.set_cache({
        #     'data': response_data,
        #     'response_headers': response_headers
        # })
        return Response(
            response_data,
            headers=response_headers
        )

    def get_cache(self):
        cache_key = (
            f'{self.request.get_full_path()}'
        )
        _cached_data = cache.get(cache_key)
        if _cached_data:
            return _cached_data
        return None

    def set_cache(self, cached_data: dict):
        cache_model_name = f'{self.cache_model.__name__}'
        cache_keys = 'cache_keys'
        cache_keys_data = cache.get(cache_keys)
        cache_key = (
            f'{self.request.get_full_path()}'
        )
        if (
                not cache_keys_data or
                cache_model_name not in cache_keys_data
        ):
            cache_keys_data = {
                cache_model_name: []
            }

        if cache_key not in cache_keys_data[cache_model_name]:
            cache_keys_data[cache_model_name].append(cache_key)

        cache.set(cache_keys, cache_keys_data, None)

        _cached_data = cache.get(cache_key)
        if not _cached_data:
            cache.set(cache_key,
                      cached_data,
                      None)
        else:
            cached_data = _cached_data
        return cached_data
