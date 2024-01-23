import logging
import os
import subprocess
from django.conf import settings
from georepo.utils.exporter_base import (
    DatasetViewExporterBase
)

logger = logging.getLogger(__name__)


class KmlViewExporter(DatasetViewExporterBase):
    output = 'kml'

    def get_base_output_dir(self) -> str:
        return settings.KML_FOLDER_OUTPUT

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        suffix = '.kml'
        kml_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = self.get_geojson_reference_file(
            resource, exported_name)
        # use ogr to convert from geojson to kml_file
        command_list = (
            [
                'ogr2ogr',
                '-f',
                'KML',
                '-overwrite',
                '-gt',
                '200',
                '-skipfailures',
                kml_file,
                geojson_file
            ]
        )
        subprocess.run(command_list)
        if not os.path.exists(kml_file):
            logger.error(f'Failed to generate KML: {kml_file}')
            return ''
        return kml_file
