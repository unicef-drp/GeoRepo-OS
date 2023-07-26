from django.core.management import BaseCommand

from georepo.utils.language import fetch_language_data


class Command(BaseCommand):

    def handle(self, *args, **options):
        fetch_language_data()
