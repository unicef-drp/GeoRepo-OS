import os
import json
import fiona
from fiona.crs import from_epsg
from uuid import UUID, uuid4
from datetime import date, datetime
from django.conf import settings

from georepo.models import (
    Dataset, DatasetView,
    DatasetViewResource
)
from georepo.utils.exporter_base import (
    DatasetExporterBase,
    DatasetViewExporterBase
)

# buffer the data before writing/flushing to file
GEOJSON_RECORDS_BUFFER_TX = 250
GEOJSON_RECORDS_BUFFER = 500


def extract_geojson_attributes(layer_file_path: str):
    """
    Load and read geojson, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with open(layer_file_path) as json_file:
        data = json.load(json_file)
        try:
            attrs = data['features'][0]['properties'].keys()
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


class GeojsonExporter(DatasetExporterBase):
    output = 'geojson'

    def write_entities(self, schema, entities, context, exported_name) -> str:
        geojson_output_folder = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(self.dataset.uuid)
        )
        if not os.path.exists(geojson_output_folder):
            os.mkdir(geojson_output_folder)
        suffix = '.geojson'
        crs = from_epsg(4326)
        output_driver = 'GeoJSON'
        tmp_filename = str(uuid4())
        tmp_geojson_file = os.path.join(
            geojson_output_folder,
            tmp_filename
        ) + suffix
        with fiona.open(tmp_geojson_file, 'w', driver=output_driver,
                        crs=crs,
                        schema=schema) as c:
            entities = entities.iterator()
            records = []
            record_count = 0
            for entity in entities:
                data = self.get_serializer()(
                    entity,
                    many=False,
                    context=context
                ).data
                records.append(data)
                record_count += 1
                if len(records) >= GEOJSON_RECORDS_BUFFER_TX:
                    c.writerecords(records)
                    records.clear()
                if record_count % GEOJSON_RECORDS_BUFFER == 0:
                    c.flush()
            if len(records) > 0:
                c.writerecords(records)
        # move the file
        geojson_file_path = os.path.join(
            geojson_output_folder,
            f'{exported_name}'
        ) + suffix
        if os.path.exists(geojson_file_path):
            os.remove(geojson_file_path)
        os.rename(tmp_geojson_file, geojson_file_path)
        return geojson_file_path


def generate_geojson(dataset: Dataset):
    """
    Extract geojson from dataset and then save it to
    geojson dataset folder
    :param dataset: Dataset object
    :return: geojson path
    """
    exporter = GeojsonExporter(dataset)
    exporter.init_exporter()
    exporter.run()


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
                          view_resource: DatasetViewResource = None):
    """
    Extract geojson from dataset_view and then save it to
    geojson dataset_view folder
    :param dataset_view: dataset_view object
    """
    exporter = GeojsonViewExporter(dataset_view, view_resource=view_resource)
    exporter.init_exporter()
    exporter.run()


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
