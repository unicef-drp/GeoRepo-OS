import os
import logging
import shutil
import json
from django.db.models.expressions import RawSQL
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.conf import settings
from django.contrib.gis.geos import WKTWriter, GEOSGeometry
from georepo.models import (
    GeographicalEntity,
    DatasetView,
    DatasetViewResource
)
from georepo.utils.azure_blob_storage import DirectoryClient
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from core.settings.utils import absolute_path
from georepo.serializers.entity import ExportCentroidGeojsonSerializer


logger = logging.getLogger(__name__)


def read_centroid_as_geojson(geom_data):
    # truncate decimal to 4 digits
    if geom_data is None:
        return '{"type": "Point", "coordinates": [0, 0]}'
    wkt_w = WKTWriter()
    wkt_w.trim = True
    wkt_w.precision = 4
    geom_wkt = wkt_w.write(GEOSGeometry(geom_data))
    return GEOSGeometry(geom_wkt).geojson


class CentroidExporter(object):
    def __init__(self, resource: DatasetViewResource):
        self.resource = resource
        self.dataset_view = resource.dataset_view
        self.privacy_level = self.resource.privacy_level
        self.total_progress = 0
        self.progress_count = 0
        self.generated_files = []
        self.levels = []

    def generate_queryset(self):
        entities = GeographicalEntity.objects.filter(
            dataset=self.dataset_view.dataset,
            is_approved=True,
            privacy_level__lte=self.privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(self.dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        return entities

    def init_exporter(self):
        self.total_progress = 0
        self.progress_count = 0
        self.generated_files = []
        # check if view at privacy level has data
        entities = self.generate_queryset()
        # count levels
        self.levels = entities.order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        self.total_progress = len(self.levels)

    def get_serializer(self):
        return ExportCentroidGeojsonSerializer

    def get_exported_file_name(self, level: int):
        exported_name = f'adm{level}'
        return exported_name

    def get_dataset_entity_query(self, entities, level: int):
        # initial fields to select
        values = [
            'id', 'label', 
            'unique_code', 'unique_code_version',
            'uuid', 'level', 'centroid'
        ]
        entities = entities.filter(
            level=level
        )
        return entities.values(*values)

    def get_base_output_dir(self) -> str:
        return settings.EXPORT_FOLDER_OUTPUT

    def get_tmp_output_dir(self) -> str:
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_centroid_{str(self.resource.uuid)}'
        )
        if not os.path.exists(tmp_output_dir):
            os.makedirs(tmp_output_dir)
        return tmp_output_dir

    def do_remove_temp_dir(self):
        tmp_output_dir = self.get_tmp_output_dir()
        if os.path.exists(tmp_output_dir):
            shutil.rmtree(tmp_output_dir)

    def run(self):
        logger.info(
            f'Exporting centroid from View {self.dataset_view.name} '
        )
        tmp_output_dir = self.get_tmp_output_dir()
        # export for each admin level
        for level in self.levels:
            logger.info(
                f'Exporting centroid of level {level} from '
                f'View {self.dataset_view.name} - {self.privacy_level}'
            )
            self.do_export(level, tmp_output_dir)
        self.do_export_post_process()
        logger.info(
            f'Exporting centroid is finished '
            f'from View {self.dataset_view.name} - {self.privacy_level}'
        )
        logger.info(self.generated_files)

    def do_export(self, level: int,
                  tmp_output_dir: str):
        exported_name = self.get_exported_file_name(level)
        entities = self.generate_queryset()
        entities = self.get_dataset_entity_query(entities, level)
        if entities.count() == 0:
            return None
        tmp_file_path = self.write_entities(
            entities,
            {},
            exported_name,
            tmp_output_dir
        )
        # TODO: convert geojson to pbf
        # exported_file_path = (
        #     f'{self.get_exported_file_name(level)}.pbf'
        # )
        exported_file_path = tmp_file_path
        if exported_file_path and os.path.exists(exported_file_path):
            self.generated_files.append(exported_file_path)
        else:
            logger.error('Failed to generate centroid '
                         f'from view {self.dataset_view.name} - {self.privacy_level}'
                         f'at level {level}')

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir) -> str:
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
                    read_centroid_as_geojson(entity['centroid'])
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

    def do_export_post_process(self):
        tmp_output_dir = self.get_tmp_output_dir()
        centroid_files = []
        # clear old directory
        self.clear_existing_resource_dir()
        # read generated files and upload it
        for level in self.levels:
            exported_name = (
                f'{self.get_exported_file_name(level)}.pbf'
            )
            tmp_file_path = os.path.join(
                tmp_output_dir,
                exported_name
            )
            if not os.path.exists(tmp_file_path):
                continue
            file_stats = os.stat(tmp_file_path)
            file_path = self.save_output_file(tmp_file_path)
            if file_path:
                centroid_files.append({
                    'path': file_path,
                    'size': file_stats.st_size,
                    'level': level
                })
        self.resource.centroid_files = centroid_files
        self.resource.save(update_fields=['centroid_files'])
        self.do_remove_temp_dir()

    def clear_existing_resource_dir(self):
        self.resource.centroid_files = []
        self.resource.save(update_fields=['centroid_files'])
        if settings.USE_AZURE:
            dir_path = os.path.join(
                'media',
                'centroid',
                str(self.resource.uuid)
            )
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            client.rmdir(dir_path)
        else:
            dir_path = os.path.join(
                settings.MEDIA_ROOT,
                'centroid',
                str(self.resource.uuid)
            )
            shutil.rmtree(dir_path)

    def save_output_file(self, tmp_file_path, exported_name):
        # save output file to non-temp directory
        if settings.USE_AZURE:
            file_path = os.path.join(
                'media',
                'centroid',
                str(self.resource.uuid),
                exported_name
            )
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            client.upload_file(tmp_file_path, file_path)
        else:
            dir_path = os.path.join(
                settings.MEDIA_ROOT,
                'centroid',
                str(self.resource.uuid)
            )
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            file_path = os.path.join(
                dir_path,
                exported_name
            )
            shutil.copyfile(tmp_file_path, file_path)
        return file_path

