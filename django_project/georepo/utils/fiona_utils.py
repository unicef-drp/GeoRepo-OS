import os
import fiona
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.temp import NamedTemporaryFile
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from fiona.collection import Collection


def open_collection(fp: str, type: str) -> Collection:
    result: Collection = None

    if settings.USE_AZURE:
        if type == 'SHAPEFILE':
            with default_storage.open(fp, 'rb') as source:
                with (
                    NamedTemporaryFile(
                        delete=False,
                        suffix='.zip',
                        dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
                    )
                ) as temp_file:
                    temp_file.write(source.read())
                    temp_file.flush()
            result = fiona.open(f'zip://{temp_file.name}', encoding='utf-8')
        else:
            with default_storage.open(fp, 'rb') as source:
                result = fiona.open(source, encoding='utf-8')
    else:
        if type == 'SHAPEFILE':
            file_path = f'zip://{fp}'
            result = fiona.open(file_path, encoding='utf-8')
        else:
            result = fiona.open(fp, encoding='utf-8')
    return result


def open_collection_by_file(fp, type: str) -> Collection:
    result: Collection = None
    file_path = None
    if settings.USE_AZURE:
        if type == 'SHAPEFILE':
            with (
                NamedTemporaryFile(
                    delete=False,
                    suffix='.zip',
                    dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
                )
            ) as temp_file:
                temp_file.write(fp.read())
                temp_file.flush()
            file_path = f'zip://{temp_file.name}'
        else:
            file_path = fp
    else:
        if type == 'SHAPEFILE':
            file_path = f'zip://{fp.path}'
        else:
            file_path = fp
    if file_path:
        result = fiona.open(file_path, encoding='utf-8')
    return result


def delete_tmp_shapefile(file_path: str):
    if settings.USE_AZURE and file_path.endswith('.zip'):
        cleaned_fp = file_path
        if '/vsizip/' in file_path:
            cleaned_fp = file_path.replace('/vsizip/', '')
        if os.path.exists(cleaned_fp):
            os.remove(cleaned_fp)


def list_layers_shapefile(fp: str):
    layers = []
    if settings.USE_AZURE:
        if isinstance(fp, InMemoryUploadedFile):
            with (
                NamedTemporaryFile(
                    delete=False,
                    suffix='.zip',
                    dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
                )
            ) as temp_file:
                temp_file.write(fp.read())
                temp_file.flush()
            layers = fiona.listlayers(f'zip://{temp_file.name}')
            delete_tmp_shapefile(temp_file.name)
        elif isinstance(fp, TemporaryUploadedFile):
            layers = fiona.listlayers(
                f'zip://{fp.temporary_file_path()}'
            )
        else:
            with default_storage.open(fp, 'rb') as source:
                with (
                    NamedTemporaryFile(
                        delete=False,
                        suffix='.zip',
                        dir=getattr(settings, 'FILE_UPLOAD_TEMP_DIR', None)
                    )
                ) as temp_file:
                    temp_file.write(source.read())
                    temp_file.flush()
            layers = fiona.listlayers(f'zip://{temp_file.name}')
            delete_tmp_shapefile(temp_file.name)
    else:
        try:
            tmp_file = None
            if isinstance(fp, InMemoryUploadedFile):
                tmp_path = os.path.join(settings.MEDIA_ROOT, 'tmp')
                if not os.path.exists(tmp_path):
                    os.makedirs(tmp_path)
                path = 'tmp/' + fp.name
                with default_storage.open(path, 'wb+') as destination:
                    for chunk in fp.chunks():
                        destination.write(chunk)
                tmp_file = os.path.join(
                    settings.MEDIA_ROOT,
                    path
                )
                layers = fiona.listlayers(f'zip://{tmp_file}')
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            elif isinstance(fp, TemporaryUploadedFile):
                layers = fiona.listlayers(
                    f'zip://{fp.temporary_file_path()}'
                )
            else:
                layers = fiona.listlayers(f'zip://{fp}')
        except Exception:
            pass
    return layers
