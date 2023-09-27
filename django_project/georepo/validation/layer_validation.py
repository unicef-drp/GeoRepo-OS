import time
import uuid


from django.db.models import IntegerField
from django.db.models.functions import Cast

from dashboard.models import (
    LayerUploadSession,
    CANCELED,
    LayerUploadSessionMetadata,
    LayerFile
)
from dashboard.models.entity_upload import EntityUploadStatus
from georepo.utils.module_import import module_function
from georepo.utils.layers import get_feature_value
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)


def validate_layer_file(entity_upload: EntityUploadStatus, **kwargs) -> bool:
    """
    Validate all layer_files from upload session against
    original geographical entity,
    then create a new revised geographical entity
    :param entity_upload: EntityUpload objects
    :return: boolean status whether the process is successful or not
    """
    dataset = entity_upload.upload_session.dataset
    module_validation = module_function(
        dataset.module.code_name,
        'qc_validation',
        'run_validation')
    return module_validation(
        entity_upload,
        **{'log_object': kwargs.get('log_object')}
    )


def read_layer_files(
    layer_files,
    **kwargs
):
    """Read all layer files default and parent codes."""
    start = time.time()
    result = {}
    for layer_file in layer_files:
        id_field = (
            [id_field['field'] for id_field in layer_file.id_fields
                if id_field['default']][0]
        )
        cache = []
        with open_collection_by_file(layer_file.layer_file,
                                     layer_file.layer_type) as layer:
            for feature in layer:
                data = {
                    id_field: (
                        str(feature['properties'][id_field])
                    )
                }
                if layer_file.parent_id_field:
                    data[layer_file.parent_id_field] = (
                        str(feature['properties'][layer_file.parent_id_field])
                    )
                cache.append(data)
            delete_tmp_shapefile(layer.path)
        result[str(layer_file.id)] = cache
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('read_layer_files', end - start)
    return result


def get_hierarchical_from_layer_file(
        layer_files,
        level,
        parent_code,
        layer_cache):
    """
    Return list of children from parent_code
    [
        'PAK_01'
        'PAK_02'
    ]
    """
    result = []
    layer_file = [x for x in layer_files if str(x.level) == str(level)]
    if len(layer_file) == 0:
        return result
    layer_file = layer_file[0]
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    if str(layer_file.id) in layer_cache:
        cache = layer_cache[str(layer_file.id)]
        result = [f[id_field] for f in cache if
                  f[layer_file.parent_id_field] == str(parent_code)]
        return result
    return result


def search_hierarchical(
    level,
    current_level,
    parent_code,
    layer_files,
    layer_cache,
    **kwargs
):
    """
    Search whether parent has children at specific level.

    layer_cache = {
        <layer_file_id>: [{
            <parent_id_field>: xxx
            <id_field>: xxx
        }]
    }
    """
    start = time.time()
    if level < current_level:
        # exit if current_level is greater than searched level
        return True
    codes = get_hierarchical_from_layer_file(
        layer_files, current_level, parent_code, layer_cache
    )
    found = False
    for code in codes:
        found = search_hierarchical(
            level,
            current_level + 1,
            code,
            layer_files,
            layer_cache
        )
        if found:
            break

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('search_hierarchical', end - start)
    return found


def validate_level_country(
    upload_session: LayerUploadSession,
    parent0_code,
    level,
    layer_cache=None,
    **kwargs
):
    """
    Validate whether country with parent0_code has feature in the level
    """
    start = time.time()
    layer_files = upload_session.layerfile_set.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(level_int__lte=level).order_by('level')
    if not layer_cache:
        layer_cache = read_layer_files(layer_files)
    return search_hierarchical(
        level,
        1,
        parent0_code,
        layer_files,
        layer_cache,
        **kwargs
    )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('validate_level_country', end - start)


def validate_level_admin_1(
    upload_session: LayerUploadSession,
    admin_level_1_codes,
    level,
    layer_cache=None,
    **kwargs
):
    """
    Validate whether country with parent0_code has feature in the level
    """
    start = time.time()
    if level == 1:
        # if level=1, then codes exist
        return len(admin_level_1_codes) > 0
    layer_files = upload_session.layerfile_set.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(level_int__lte=level).order_by('level')
    if not layer_cache:
        layer_cache = read_layer_files(
            layer_files,
            **kwargs
        )
    for code in admin_level_1_codes:
        result = search_hierarchical(
            level,
            2,
            code,
            layer_files,
            layer_cache,
            **kwargs
        )
        if result:
            return True
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('validate_level_admin_1', end - start)
    return False


def retrieve_layer0_default_codes(
        upload_session: LayerUploadSession,
        default_max_level=None,
        overwrite=False):
    """Retrieve a list of default codes from layer_file level 0"""
    layer0_default_codes = []
    layer_files = upload_session.layerfile_set.filter(level=0)
    if not layer_files.exists():
        return layer0_default_codes
    if upload_session.status == CANCELED:
        return layer0_default_codes
    if not overwrite:
        session_metadata = LayerUploadSessionMetadata.objects.filter(
            session=upload_session
        ).first()
        if session_metadata and session_metadata.adm0_default_codes:
            return session_metadata.adm0_default_codes
    layer_file: LayerFile = layer_files.first()
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    name_field = (
        [name_field['field'] for name_field in layer_file.name_fields
            if name_field['default']][0]
    )
    if not layer_file.layer_file.storage.exists(layer_file.layer_file.name):
        return layer0_default_codes
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as features:
        for feature in features:
            layer0_default_codes.append({
                'id': str(uuid.uuid4()),
                'country': get_feature_value(feature, name_field, 'Unknown'),
                'layer0_id': (
                    str(feature['properties'][id_field]) if
                    id_field in feature['properties'] else None
                ),
                'country_entity_id': None,
                'layer0_file': layer_file.layer_file.name.split('/')[-1],
                'revision': None,
                'max_level': default_max_level
            })
        delete_tmp_shapefile(features.path)
    session_metadata, _ = LayerUploadSessionMetadata.objects.get_or_create(
        session=upload_session
    )
    session_metadata.adm0_default_codes = layer0_default_codes
    session_metadata.total_adm0 = len(layer0_default_codes)
    session_metadata.save()
    return layer0_default_codes
