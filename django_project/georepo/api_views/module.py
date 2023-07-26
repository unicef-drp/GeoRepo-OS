import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi
from django.core.paginator import Paginator
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from georepo.serializers.module import ModuleSerializer
from georepo.models.module import Module
from georepo.utils.url_helper import get_page_size
from georepo.api_views.api_collections import SEARCH_MODULE_TAG
from georepo.utils.api_parameters import common_api_params


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
                operation_id='search-module-list',
                tags=[SEARCH_MODULE_TAG],
                manual_parameters=common_api_params,
                responses={
                    200: openapi.Schema(
                        title='Module List',
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'page': openapi.Schema(
                                title='Page Number',
                                type=openapi.TYPE_INTEGER
                            ),
                            'total_page': openapi.Schema(
                                title='Total Page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'page_size': openapi.Schema(
                                title='Total item in 1 page',
                                type=openapi.TYPE_INTEGER
                            ),
                            'results': openapi.Schema(
                                title='List of module',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties=(
                                        ModuleSerializer.Meta.
                                        swagger_schema_fields['properties']
                                    )
                                ),
                            )
                        },
                        example={
                            'page': 1,
                            'total_page': 10,
                            'page_size': 10,
                            'results': [
                                (
                                    ModuleSerializer.Meta.
                                    swagger_schema_fields['example']
                                )
                            ]
                        }
                    )
                }
            )
)
class ModuleList(APIView):
    """
    Get modules

    Return modules:
    - name
    - description
    - uuid
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        page = int(request.GET.get('page', '1'))
        page_size = get_page_size(request)

        modules = Module.objects.filter(
            is_active=True
        ).order_by('id')
        # set pagination
        paginator = Paginator(modules, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                ModuleSerializer(
                    paginated_entities,
                    many=True
                ).data
            )
        return Response(status=200, data={
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        })
