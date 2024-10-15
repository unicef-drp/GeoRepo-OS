import os
import json
import logging
import subprocess
from uuid import UUID
from datetime import date, datetime

from georepo.models import (
    ExportRequestStatusText,
    SHAPEFILE_EXPORT_TYPE,
    KML_EXPORT_TYPE,
    TOPOJSON_EXPORT_TYPE,
    GEOPACKAGE_EXPORT_TYPE
)
from georepo.utils.exporter_base import (
    DatasetViewExporterBase
)
from georepo.utils.fiona_utils import (
    open_collection_by_file
)


logger = logging.getLogger(__name__)
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

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file) -> str:
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
                geom_data = entity['rhr_geom']
                if geom_data is None:
                    geom_data = '{"type": "Point", "coordinates": [0, 0]}'
                feature_str = feature_str.replace(
                    '"{geom_placeholder}"',
                    geom_data
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


class GeojsonBasedExporter(DatasetViewExporterBase):

    def init_exporter(self):
        super().init_exporter()
        # create geojson exporter
        self.geojson_exporter = GeojsonViewExporter(
            self.request, True, self
        )
        self.geojson_exporter.init_exporter()

    def get_geojson_reference_file(self, exported_name):
        file_path = f'{exported_name}.geojson'
        return os.path.join(
            self.get_base_output_dir(),
            f'temp_{str(self.request.uuid)}',
            file_path
        )

    def get_preparing_status_by_format(self):
        if self.request.format == SHAPEFILE_EXPORT_TYPE:
            return ExportRequestStatusText.PREPARING_SHP
        elif self.request.format == KML_EXPORT_TYPE:
            return ExportRequestStatusText.PREPARING_KML
        elif self.request.format == TOPOJSON_EXPORT_TYPE:
            return ExportRequestStatusText.PREPARING_TOPOJSON
        elif self.request.format == GEOPACKAGE_EXPORT_TYPE:
            return ExportRequestStatusText.PREPARING_GPKG
        return ExportRequestStatusText.PREPARING_GEOJSON

    def run(self):
        self.update_progress_text(
            ExportRequestStatusText.PREPARING_GEOJSON
        )
        # extract the geojson first
        self.geojson_exporter.run()
        # validate geojson files are extracted successfully
        if len(self.geojson_exporter.generated_files) != len(self.levels):
            logger.error(
                'Failed to generate geojson files '
                f'for {self.format} exporter!'
            )
            return
        # run exporter for shapefile
        self.update_progress_text(
            self.get_preparing_status_by_format()
        )
        super().run()

    def get_env(self) -> dict:
        """Get dictionary env variables for running ogr2ogr.

        :return: environment variables
        :rtype: dict
        """
        return os.environ.copy()

    def do_conversion(self, command_list):
        logger.info(command_list)
        my_env = self.get_env()
        result = subprocess.run(command_list, capture_output=True, env=my_env)
        logger.info(f'{self.request.format} conversion '
                    f'result_code: {result.returncode}')
        if result.returncode != 0:
            logger.error(result.stderr.decode())
            raise RuntimeError(result.stderr.decode())


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
