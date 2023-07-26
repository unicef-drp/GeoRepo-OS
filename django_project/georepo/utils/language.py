import requests
import logging

from django.http import Http404

from georepo.models.language import Language

logger = logging.getLogger(__name__)

REST_URL = (
    'https://restcountries.com/v2/all?fields=name,languages'
)
ISO_CODE = 'iso639_1'


def fetch_language_data():
    try:
        response = requests.get(REST_URL)
    except requests.exceptions.ConnectionError as errc:
        logger.error('Error connect : ', errc)
        raise Http404('Error connecting')
    countries = response.json()
    for country in countries:
        for language in country['languages']:
            if ISO_CODE in language:
                Language.objects.get_or_create(
                    code=language[ISO_CODE].upper(),
                    name=language['name'],
                    defaults={
                        'native_name': (
                            language['nativeName'] if 'nativeName' in language
                            else ''
                        )
                    }
                )
