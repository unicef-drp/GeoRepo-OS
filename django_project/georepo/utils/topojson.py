import logging
import os
import subprocess
from django.conf import settings
from georepo.models import (
    DatasetView,
    DatasetViewResource
)
from georepo.utils.exporter_base import (
    DatasetViewExporterBase
)

logger = logging.getLogger(__name__)


class TopojsonViewExporter(DatasetViewExporterBase):
    output = 'topojson'

    def get_base_output_dir(self) -> str:
        return settings.TOPOJSON_FOLDER_OUTPUT

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        suffix = '.topojson'
        topojson_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(resource.uuid),
            exported_name
        ) + '.geojson'
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
        if not os.path.exists(topojson_file):
            logger.error(f'Failed to generate Topojson: {topojson_file}')
            return ''
        return topojson_file


def generate_view_topojson(dataset_view: DatasetView,
                           view_resource: DatasetViewResource = None):
    """
    Extract topojson from dataset_view and then save it to
    topojson dataset_view folder
    :param dataset: dataset_view object
    """
    exporter = TopojsonViewExporter(dataset_view,
                                    view_resource=view_resource)
    exporter.init_exporter()
    exporter.run()
