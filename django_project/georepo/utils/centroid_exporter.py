import os
import logging
import shutil
import json
import subprocess
import traceback
from django.db.models.expressions import RawSQL
from django.conf import settings
from django.contrib.gis.geos import WKTWriter, GEOSGeometry
from django.utils import timezone
from georepo.models import (
    GeographicalEntity,
    DatasetViewResource
)
from georepo.utils.azure_blob_storage import DirectoryClient
from georepo.serializers.entity import ExportCentroidGeojsonSerializer


logger = logging.getLogger(__name__)


def read_centroid_as_geojson(geom_data):
    # truncate decimal to 4 digits
    if geom_data is None or geom_data == '':
        return '{"type":"Point","coordinates":[0,0]}'
    wkt_w = WKTWriter()
    wkt_w.trim = True
    wkt_w.precision = 4
    geom_wkt = wkt_w.write(GEOSGeometry(geom_data))
    return GEOSGeometry(geom_wkt).geojson.replace(' ', '')


def convert_geojson_to_gz(file_path, output_dir, exported_name):
    command_list = (
        [
            'gzip',
            file_path
        ]
    )
    logger.info(command_list)
    result = subprocess.run(command_list)
    if result.returncode != 0:
        return None
    return os.path.join(
        output_dir,
        f'{exported_name}.geojson.gz'
    )


def clean_resource_centroid_cache_dir(resource_uuid):
    if settings.USE_AZURE:
        dir_path = os.path.join(
            'media',
            'centroid',
            str(resource_uuid)
        )
        client = DirectoryClient(settings.AZURE_STORAGE,
                                 settings.AZURE_STORAGE_CONTAINER)
        client.rmdir(dir_path)
    else:
        dir_path = os.path.join(
            settings.MEDIA_ROOT,
            'centroid',
            str(resource_uuid)
        )
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)


def clean_exporter_temp_output_dir(resource_uuid):
    tmp_output_dir = os.path.join(
        CentroidExporter.get_base_output_dir(),
        f'temp_centroid_{str(resource_uuid)}'
    )
    if os.path.exists(tmp_output_dir):
        shutil.rmtree(tmp_output_dir)


class CentroidExporter(object):
    output_suffix = '.geojson'

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
        self.total_progress = len(self.levels) + 1
        # remove tmp_output_dir
        self.do_remove_temp_dir()
        self.resource.centroid_sync_progress = 0
        self.resource.centroid_sync_status = (
            DatasetViewResource.SyncStatus.SYNCING
        )
        self.resource.save(update_fields=['centroid_sync_progress',
                                          'centroid_sync_status'])

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
            'uuid', 'level', 'centroid', 'bbox'
        ]
        entities = entities.filter(
            level=level
        )
        # add parents to the query
        related = ''
        for i in range(level):
            related = related + (
                '__parent' if i > 0 else 'parent'
            )
            # fetch parent's default code
            values.append(f'{related}__uuid')
            values.append(f'{related}__unique_code')
            values.append(f'{related}__unique_code_version')
        entities = entities.order_by('label')
        return entities.values(*values)

    @staticmethod
    def get_base_output_dir() -> str:
        return settings.EXPORT_FOLDER_OUTPUT

    def get_tmp_output_dir(self, auto_create=True) -> str:
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_centroid_{str(self.resource.uuid)}'
        )
        if not os.path.exists(tmp_output_dir) and auto_create:
            os.makedirs(tmp_output_dir)
        return tmp_output_dir

    def do_remove_temp_dir(self):
        tmp_output_dir = self.get_tmp_output_dir()
        if os.path.exists(tmp_output_dir):
            shutil.rmtree(tmp_output_dir)

    def update_progress(self, inc_progress = 1):
        self.progress_count += inc_progress
        self.resource.centroid_sync_progress = (
            (self.progress_count * 100) / self.total_progress
        ) if self.total_progress > 0 else 0
        self.resource.save(update_fields=['centroid_sync_progress'])

    def run(self):
        logger.info(
            f'Exporting centroid from View {self.dataset_view.name} '
        )
        try:
            tmp_output_dir = self.get_tmp_output_dir()
            # export for each admin level
            for level in self.levels:
                logger.info(
                    f'Exporting centroid of level {level} from '
                    f'View {self.dataset_view.name} - {self.privacy_level}'
                )
                self.do_export(level, tmp_output_dir)
                self.update_progress()
            self.do_export_post_process()
            logger.info(
                f'Exporting centroid is finished '
                f'from View {self.dataset_view.name} - {self.privacy_level}'
            )
            logger.info(self.generated_files)
        except Exception as ex:
            logger.error('Failed Process Centroid Exporter!')
            logger.error(ex)
            logger.error(traceback.format_exc())
            self.resource.centroid_sync_status = (
                DatasetViewResource.SyncStatus.ERROR
            )
            self.resource.save(update_fields=['centroid_sync_status'])
            self.do_remove_temp_dir()

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
        # convert geojson to pbf
        exported_file_path = convert_geojson_to_gz(
            tmp_file_path, tmp_output_dir, exported_name)
        if exported_file_path and os.path.exists(exported_file_path):
            file_stats = os.stat(exported_file_path)
            self.generated_files.append({
                    'path': exported_file_path,
                    'size': file_stats.st_size,
                    'level': level
            })
        else:
            logger.error('Failed to generate centroid '
                         f'from view {self.dataset_view.name} '
                         f'- {self.privacy_level} '
                         f'at level {level}')

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir) -> str:
        suffix = '.geojson'
        geojson_file_path = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        with open(geojson_file_path, "w") as geojson_file:
            geojson_file.write('{')
            geojson_file.write('"type":"FeatureCollection",')
            geojson_file.write('"features":[')
            idx = 0
            total_count = entities.count()
            for entity in entities.iterator(chunk_size=1):
                data = self.get_serializer()(
                    entity,
                    many=False,
                    context=context
                ).data
                data['geometry'] = '{geom_placeholder}'
                feature_str = json.dumps(data, separators=(',', ':'))
                feature_str = feature_str.replace(
                    '"{geom_placeholder}"',
                    read_centroid_as_geojson(entity['centroid'])
                )
                geojson_file.write(feature_str)
                if idx == total_count - 1:
                    pass
                else:
                    geojson_file.write(',')
                idx += 1
            geojson_file.write(']')
            geojson_file.write('}')
        return geojson_file_path

    def do_export_post_process(self):
        centroid_files = []
        # clear old directory
        self.clear_existing_resource_dir()
        # read generated files and upload it
        for generated_file in self.generated_files:
            level = generated_file['level']
            exported_name = (
                f'{self.get_exported_file_name(level)}{self.output_suffix}'
            )
            file_path = self.save_output_file(
                generated_file['path'], exported_name)
            if file_path:
                centroid_files.append({
                    'path': file_path,
                    'size': generated_file['size'],
                    'level': level
                })
        self.resource.centroid_files = centroid_files
        self.resource.centroid_sync_status = (
            DatasetViewResource.SyncStatus.SYNCED
        )
        self.resource.centroid_sync_progress = 100
        self.resource.centroid_updated_at = timezone.now()
        self.resource.save(update_fields=['centroid_files',
                                          'centroid_sync_status',
                                          'centroid_sync_progress',
                                          'centroid_updated_at'])
        self.do_remove_temp_dir()

    def clear_existing_resource_dir(self):
        self.resource.centroid_files = []
        self.resource.save(update_fields=['centroid_files'])
        clean_resource_centroid_cache_dir(self.resource.uuid)
        self.resource.clear_centroid_cache()

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
            max_age = settings.EXPORT_DATA_EXPIRY_IN_HOURS * 3600
            client.upload_gzip_file(
                tmp_file_path,
                file_path,
                cache_control=f'private, max-age={max_age}'
            )
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
