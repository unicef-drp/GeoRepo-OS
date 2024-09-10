import time
from typing import Tuple, List

from georepo.models import (
    GeographicalEntity
)
from georepo.validation.layer_validation import (
    retrieve_layer0_default_codes
)
from dashboard.models import (
    LayerUploadSession, EntityUploadStatus
)
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)


def validate_layer_file_0(
        upload_session: LayerUploadSession) -> Tuple[bool, str]:
    """
    Return True, None if all entity in layer file 0 has unique default code
    else return False, duplicateDefaultCode.
    create_temp_entity = Generate temporary entities for admin level 0
    for auto parent matching. This parameter value may be False if there is no
    admin level 1 uploads.
    """
    # find layer file level 0 from the session
    layer_files = upload_session.layerfile_set.filter(level=0)
    if not layer_files.exists():
        # ignore if no layer file 0 exists
        return True
    layer_file_0 = layer_files.first()
    id_field = (
        [id_field['field'] for id_field in layer_file_0.id_fields
            if id_field['default']][0]
    )
    layer0_default_codes = []
    is_valid = True
    duplicate_code = None
    with open_collection_by_file(layer_file_0.layer_file,
                                 layer_file_0.layer_type) as features:
        for feature in features:
            # default code
            entity_id = (
                str(feature['properties'][id_field]) if
                id_field in feature['properties'] else None
            )
            if not entity_id:
                # skip if entity_id not found
                continue
            if entity_id in layer0_default_codes:
                is_valid = False
                duplicate_code = entity_id
                break
            layer0_default_codes.append(entity_id)
        delete_tmp_shapefile(features.path)
    return is_valid, duplicate_code


def preprocess_layer_file_0(
    upload_session: LayerUploadSession,
    **kwargs
) -> List[EntityUploadStatus]:
    """
    Read layer files level 0 and create entity uploads object
    """
    start = time.time()
    level_0_data = retrieve_layer0_default_codes(upload_session,
                                                 overwrite=True)
    entities = GeographicalEntity.objects.filter(
        dataset=upload_session.dataset,
        level=0,
        is_approved=True,
        is_latest=True
    ).order_by('uuid').distinct('uuid')
    results = []
    # merge level_0_data from layer_file with existing level0 data
    for entity in entities:
        layer0 = (
            [(layer0, idx) for idx, layer0 in
                enumerate(level_0_data)
                if layer0['layer0_id'] == entity.internal_code]
        )
        if layer0:
            entity_upload, _ = (
                EntityUploadStatus.objects.update_or_create(
                    upload_session=upload_session,
                    original_geographical_entity=entity
                )
            )
            results.append(entity_upload)
            del level_0_data[layer0[0][1]]
    for layer0 in level_0_data:
        if layer0['layer0_id']:
            entity_upload, _ = (
                EntityUploadStatus.objects.update_or_create(
                    upload_session=upload_session,
                    revised_entity_id=layer0['layer0_id'],
                    revised_entity_name=layer0['country']
                )
            )
            results.append(entity_upload)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'preprocess_layer_file_0',
            end - start
        )
    return results
