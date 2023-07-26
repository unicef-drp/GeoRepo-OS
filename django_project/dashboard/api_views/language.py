from rest_framework.response import Response
from rest_framework.views import APIView

from azure_auth.backends import AzureAuthRequiredMixin
from georepo.api_views.api_cache import ApiCache
from georepo.models.language import Language
from georepo.serializers.language import LanguageSerializer
from georepo.utils.language import fetch_language_data


class LanguageList(ApiCache):
    """
    View to list all languages
    """
    cache_model = Language
    use_cache = False

    def get_response_data(self, request, *args, **kwargs):
        languages = Language.objects.all().order_by(
            'order',
            'name'
        )
        serializer = LanguageSerializer(
            languages,
            many=True
        )
        return serializer.data, None


class FetchLanguages(AzureAuthRequiredMixin, APIView):
    def post(self, request, **kwargs):
        fetch_language_data()
        return Response(status=201)
