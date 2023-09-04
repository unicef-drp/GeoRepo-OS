from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
import fiona
from fiona.io import (
    MemoryFile
)
from fiona.crs import from_epsg
from georepo.utils.shapefile import store_zip_memory_to_temp_file
from georepo.utils.fiona_utils import open_collection, delete_tmp_shapefile


def get_crs_epsg(crs):
    return crs['init'] if 'init' in crs else None


def validate_layer_file_in_crs_4326(layer_file_obj: any, type: any):
    """Validate crs to be EPSG:4326"""
    epsg_mapping = from_epsg(4326)
    valid = False
    crs = None
    # if less than <2MB, it will be InMemoryUploadedFile
    if isinstance(layer_file_obj, InMemoryUploadedFile):
        if type == 'SHAPEFILE':
            # fiona having issues with reading ZipMemoryFile
            # need to store to temp file
            tmp_file = store_zip_memory_to_temp_file(layer_file_obj)
            with open_collection(tmp_file, type) as collection:
                valid = get_crs_epsg(collection.crs) == epsg_mapping['init']
                crs = get_crs_epsg(collection.crs)
            default_storage.delete(tmp_file)
            delete_tmp_shapefile(collection.path)
        else:
            # geojson/geopackage can be read using MemoryFile
            with MemoryFile(layer_file_obj.file) as file:
                with file.open() as collection:
                    valid = (
                        get_crs_epsg(collection.crs) == epsg_mapping['init']
                    )
                    crs = get_crs_epsg(collection.crs)
    else:
        # TemporaryUploadedFile or just string to file path
        file_path = layer_file_obj
        if type == 'SHAPEFILE':
            if isinstance(layer_file_obj, TemporaryUploadedFile):
                file_path = f'zip://{layer_file_obj.temporary_file_path()}'
                with fiona.open(file_path) as collection:
                    valid = get_crs_epsg(collection.crs) == epsg_mapping['init']
                    crs = get_crs_epsg(collection.crs)
            else:
                with open_collection(file_path, type) as collection:
                    valid = get_crs_epsg(collection.crs) == epsg_mapping['init']
                    crs = get_crs_epsg(collection.crs)
        else:
            with open_collection(file_path, type) as collection:
                valid = get_crs_epsg(collection.crs) == epsg_mapping['init']
                crs = get_crs_epsg(collection.crs)
    return valid, crs
