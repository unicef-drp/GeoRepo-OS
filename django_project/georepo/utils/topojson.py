import logging
import os
from georepo.utils.geojson import (
    GeojsonBasedExporter,
    GeojsonDatasetBasedExporter
)


logger = logging.getLogger(__name__)


class TopojsonBaseExporter:

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
        self.do_conversion(command_list)
        return topojson_file


class TopojsonViewExporter(TopojsonBaseExporter, GeojsonBasedExporter):

    pass


class TopojsonDatasetExporter(
    TopojsonBaseExporter, GeojsonDatasetBasedExporter
):

    pass
