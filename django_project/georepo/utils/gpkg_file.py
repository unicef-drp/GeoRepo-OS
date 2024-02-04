import os
import logging
import subprocess
from georepo.utils.geojson import (
    GeojsonBasedExporter
)
from georepo.utils.fiona_utils import open_collection_by_file


logger = logging.getLogger(__name__)


def extract_gpkg_attributes(layer_file):
    """
    Load and read geopackage file, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with open_collection_by_file(layer_file, 'GPKG') as collection:
        try:
            attrs = next(iter(collection))["properties"].keys()
        except (KeyError, IndexError):
            pass
    return attrs


def get_gpkg_feature_count(layer_file):
    """
    Get Feature count in shape file
    """
    feature_count = 0
    with open_collection_by_file(layer_file, 'GPKG') as collection:
        feature_count = len(collection)
    return feature_count


class GPKGViewExporter(GeojsonBasedExporter):

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file) -> str:
        suffix = '.gpkg'
        gpkg_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = self.get_geojson_reference_file(exported_name)
        # use ogr to convert from geojson to kml_file
        command_list = (
            [
                'ogr2ogr',
                '-f',
                'GPKG',
                '-overwrite',
                '-gt',
                '200',
                gpkg_file,
                geojson_file
            ]
        )
        logger.info(command_list)
        result = subprocess.run(command_list)
        logger.info(f'GPKG conversion result_code: {result.returncode}')
        return gpkg_file
