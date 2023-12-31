import os
import json
import time
from uuid import UUID
from datetime import date, datetime
from django.conf import settings

from georepo.models import (
    Dataset, DatasetView,
    DatasetViewResource
)
from georepo.utils.exporter_base import (
    DatasetViewExporterBase
)
from georepo.utils.fiona_utils import (
    open_collection_by_file
)

# buffer the data before writing/flushing to file
GEOJSON_RECORDS_BUFFER_TX = 250
GEOJSON_RECORDS_BUFFER = 500


def get_geojson_feature_count(layer_file):
    """
    Get Feature count in geojson file
    """
    feature_count = 0
    with open_collection_by_file(layer_file, 'GEOJSON') as collection:
        feature_count = len(collection)
    return feature_count


def extract_geojson_attributes(layer_file):
    """
    Load and read geojson, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with open_collection_by_file(layer_file, 'GEOJSON') as collection:
        try:
            attrs = next(iter(collection))["properties"].keys()
        except (KeyError, IndexError):
            pass
    return attrs


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError("Type %s not serializable" % type(obj))


class GeojsonViewExporter(DatasetViewExporterBase):
    output = 'geojson'

    def get_base_output_dir(self) -> str:
        return settings.GEOJSON_FOLDER_OUTPUT

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        suffix = '.geojson'
        geojson_file_path = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        with open(geojson_file_path, "w") as geojson_file:
            geojson_file.write('{\n')
            geojson_file.write('"type": "FeatureCollection",\n')
            geojson_file.write('"features": [\n')
            idx = 0
            total_count = entities.count()
            for entity in entities.iterator(chunk_size=1):
                data = self.get_serializer()(
                    entity,
                    many=False,
                    context=context
                ).data
                data['geometry'] = '{geom_placeholder}'
                feature_str = json.dumps(data)
                feature_str = feature_str.replace(
                    '"{geom_placeholder}"',
                    entity['rhr_geom']
                )
                geojson_file.write(feature_str)
                if idx == total_count - 1:
                    geojson_file.write('\n')
                else:
                    geojson_file.write(',\n')
                idx += 1
            geojson_file.write(']\n')
            geojson_file.write('}\n')
        return geojson_file_path


def generate_view_geojson(dataset_view: DatasetView,
                          view_resource: DatasetViewResource = None,
                          **kwargs):
    """
    Extract geojson from dataset_view and then save it to
    geojson dataset_view folder
    :param dataset_view: dataset_view object
    """
    start = time.time()
    exporter = GeojsonViewExporter(dataset_view, view_resource=view_resource)
    exporter.init_exporter()
    exporter.run()
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'generate_view_geojson',
            end - start)
    return exporter


def validate_geojson(geojson: dict) -> bool:
    f_type_list = [
        'FeatureCollection',
        'Feature'
    ]
    if 'type' not in geojson:
        return False
    f_type = geojson['type']
    if f_type not in f_type_list:
        return False
    if f_type == 'FeatureCollection' and 'features' not in geojson:
        return False
    if (f_type == 'FeatureCollection' and
            (not isinstance(geojson['features'], list) or
                not geojson['features'])):
        return False
    if (f_type == 'Feature' and 'geometry' not in geojson):
        return False
    return True


def delete_geojson_file(dataset: Dataset):
    """
    Delete extracted geojson file when dataset is deleted
    """
    suffix = '.geojson'
    geojson_file_path = os.path.join(
        settings.GEOJSON_FOLDER_OUTPUT,
        str(dataset.uuid)
    ) + suffix
    if os.path.exists(geojson_file_path):
        os.remove(geojson_file_path)
