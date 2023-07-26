from django.core.management import BaseCommand

from georepo.models import EntityType
from georepo.utils.load_layer_file import load_layer_file


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--geojson_file',
            required=True
        )
        parser.add_argument(
            '--level'
        )
        parser.add_argument(
            '--name_field'
        )
        parser.add_argument(
            '--code_field'
        )
        parser.add_argument(
            '--dataset'
        )
        parser.add_argument(
            '--type',
            required=True
        )
        parser.add_argument(
            '--parent_field'
        )

    def handle(self, *args, **options):

        entity_type, created = EntityType.objects.get_or_create(
            label=options['type']
        )

        geojson_loaded, message = load_layer_file(
            'GEOJSON',
            options['geojson_file'],
            int(options['level']),
            entity_type,
            options['name_field'],
            options['dataset'],
            options['code_field']
        )

        print('Geojson loaded : {}'.format(geojson_loaded))
