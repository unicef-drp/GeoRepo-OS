import fiona
from fiona.crs import from_epsg
import zipfile
import os
import subprocess
from uuid import uuid4
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from georepo.models import (
    Dataset, DatasetView,
    DatasetViewResource
)
from georepo.utils.exporter_base import (
    DatasetExporterBase,
    DatasetViewExporterBase
)

# buffer the data before writing/flushing to file
SHAPEFILE_RECORDS_BUFFER_TX = 400
SHAPEFILE_RECORDS_BUFFER = 800

GENERATED_FILES = ['.shp', '.dbf', '.shx', '.cpg', '.prj']


def extract_shapefile_attributes(layer_file_path: str):
    """
    Load and read shape file, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with fiona.open(f'zip://{layer_file_path}') as collection:
        try:
            attrs = next(iter(collection))["properties"].keys()
        except (KeyError, IndexError):
            pass
    return attrs


def get_shape_file_feature_count(layer_file_path: str):
    """
    Get Feature count in shape file
    """
    feature_count = 0
    with fiona.open(f'zip://{layer_file_path}') as collection:
        feature_count = len(collection)
    return feature_count


def store_zip_memory_to_temp_file(file_obj: InMemoryUploadedFile):
    tmp_path = os.path.join(settings.MEDIA_ROOT, 'tmp')
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    path = 'tmp/' + file_obj.name
    with default_storage.open(path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    tmp_file = os.path.join(settings.MEDIA_ROOT, path)
    return tmp_file


def validate_shapefile_zip(layer_file_path: any):
    """
    Validate if shapefile zip has correct necessary files
    Note: fiona will throw exception only if dbf or shx is missing
    if there are 2 layers inside the zip, and 1 of them is invalid,
    then fiona will only return 1 layer
    """
    layers = []
    try:
        tmp_file = None
        if isinstance(layer_file_path, InMemoryUploadedFile):
            tmp_file = store_zip_memory_to_temp_file(layer_file_path)
            layers = fiona.listlayers(f'zip://{tmp_file}')
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        elif isinstance(layer_file_path, TemporaryUploadedFile):
            layers = fiona.listlayers(
                f'zip://{layer_file_path.temporary_file_path()}'
            )
        else:
            layers = fiona.listlayers(f'zip://{layer_file_path}')
    except Exception:
        pass
    is_valid = len(layers) > 0
    error = []
    names = []
    with zipfile.ZipFile(layer_file_path, 'r') as zipFile:
        names = zipFile.namelist()
    shp_files = [n for n in names if n.endswith('.shp')]
    shx_files = [n for n in names if n.endswith('.shx')]
    dbf_files = [n for n in names if n.endswith('.dbf')]

    if is_valid:
        for filename in layers:
            if f'{filename}.shp' not in shp_files:
                error.append(f'{filename}.shp')
            if f'{filename}.shx' not in shx_files:
                error.append(f'{filename}.shx')
            if f'{filename}.dbf' not in dbf_files:
                error.append(f'{filename}.dbf')
    else:
        distinct_files = (
            [
                os.path.splitext(shp)[0] for shp in shp_files
            ] +
            [
                os.path.splitext(shx)[0] for shx in shx_files
            ] +
            [
                os.path.splitext(dbf)[0] for dbf in dbf_files
            ]
        )
        distinct_files = list(set(distinct_files))
        if len(distinct_files) == 0:
            error.append('No required .shp file')
        else:
            for filename in distinct_files:
                if f'{filename}.shp' not in shp_files:
                    error.append(f'{filename}.shp')
                if f'{filename}.shx' not in shx_files:
                    error.append(f'{filename}.shx')
                if f'{filename}.dbf' not in dbf_files:
                    error.append(f'{filename}.dbf')
    is_valid = is_valid and len(error) == 0
    return is_valid, error


class ShapefileExporter(DatasetExporterBase):
    output = 'shapefile'

    def write_entities(self, schema, entities, context, exported_name) -> str:
        shapefile_output_folder = os.path.join(
            settings.SHAPEFILE_FOLDER_OUTPUT,
            str(self.dataset.uuid)
        )
        if not os.path.exists(shapefile_output_folder):
            os.mkdir(shapefile_output_folder)
        suffix = '.shp'
        crs = from_epsg(4326)
        output_driver = 'ESRI Shapefile'
        tmp_filename = str(uuid4())
        shape_file = os.path.join(
            shapefile_output_folder,
            tmp_filename
        ) + suffix
        with fiona.open(shape_file, 'w', driver=output_driver,
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
                if len(records) >= SHAPEFILE_RECORDS_BUFFER_TX:
                    c.writerecords(records)
                    records.clear()
                if record_count % SHAPEFILE_RECORDS_BUFFER == 0:
                    c.flush()
            if len(records) > 0:
                c.writerecords(records)
        # zip all the files
        tmp_zip_file_path = os.path.join(
            shapefile_output_folder,
            f'tmp_{exported_name}'
        ) + '.zip'
        with zipfile.ZipFile(
                tmp_zip_file_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for suffix in GENERATED_FILES:
                shape_file = os.path.join(
                    shapefile_output_folder,
                    tmp_filename
                ) + suffix
                if not os.path.exists(shape_file):
                    continue
                archive.write(
                    shape_file,
                    arcname=exported_name + suffix
                )
                os.remove(shape_file)
        # move zip file
        zip_file_path = os.path.join(
            shapefile_output_folder,
            f'{exported_name}'
        ) + '.zip'
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        os.rename(tmp_zip_file_path, zip_file_path)
        return zip_file_path


def generate_shapefile(dataset: Dataset):
    """
    Extract shape file from dataset and then save it to
    shapefile dataset folder
    :param dataset: Dataset object
    :return: shapefile path
    """
    exporter = ShapefileExporter(dataset)
    exporter.init_exporter()
    exporter.run()


class ShapefileViewExporter(DatasetViewExporterBase):
    output = 'shapefile'

    def get_base_output_dir(self) -> str:
        return settings.SHAPEFILE_FOLDER_OUTPUT

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        suffix = '.shp'
        shape_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(resource.uuid),
            exported_name
        ) + '.geojson'
        # use ogr to convert from geojson to shapefile
        command_list = (
            [
                'ogr2ogr',
                '-f',
                'ESRI Shapefile',
                '-overwrite',
                '-gt',
                '200',
                '-skipfailures',
                shape_file,
                geojson_file
            ]
        )
        subprocess.run(command_list)
        # zip all the files
        zip_file_path = os.path.join(
            tmp_output_dir,
            f'{exported_name}'
        ) + '.zip'
        with zipfile.ZipFile(
                zip_file_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for suffix in GENERATED_FILES:
                shape_file = os.path.join(
                    tmp_output_dir,
                    exported_name
                ) + suffix
                if not os.path.exists(shape_file):
                    continue
                archive.write(
                    shape_file,
                    arcname=exported_name + suffix
                )
                os.remove(shape_file)
            # add metadata
            archive.write(
                tmp_metadata_file,
                arcname=exported_name + '.xml'
            )
            os.remove(tmp_metadata_file)
        return zip_file_path


def generate_view_shapefile(dataset_view: DatasetView,
                            view_resource: DatasetViewResource = None):
    """
    Extract shape file from dataset_view and then save it to
    shapefile dataset_view folder
    :param dataset: dataset_view object
    """
    exporter = ShapefileViewExporter(dataset_view,
                                     view_resource=view_resource)
    exporter.init_exporter()
    exporter.run()
