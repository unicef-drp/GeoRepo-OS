import logging
import os
import subprocess
from georepo.utils.geojson import GeojsonBasedExporter


logger = logging.getLogger(__name__)


class TopojsonViewExporter(GeojsonBasedExporter):

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file) -> str:
        suffix = '.topojson'
        topojson_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = self.get_geojson_reference_file(exported_name)
        # use ogr to convert from geojson to topojson_file
        command_list = (
            [
                'geo2topo',
                '-o',
                topojson_file,
                geojson_file
            ]
        )
        subprocess.run(command_list)
        return topojson_file
