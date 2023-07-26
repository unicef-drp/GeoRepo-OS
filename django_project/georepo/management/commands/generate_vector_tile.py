from django.core.management import BaseCommand

from georepo.models import Dataset
from georepo.utils.vector_tile import generate_vector_tiles


class Command(BaseCommand):

    def handle(self, *args, **options):
        generate_vector_tiles(Dataset.objects.first())
