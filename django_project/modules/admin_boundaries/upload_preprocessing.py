import time
import json
from typing import Tuple
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from core.celery import app
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PRE_PROCESSING, PENDING
)
from dashboard.models.entity_upload import EntityTemp
from dashboard.models.layer_file import LayerFile
from modules.admin_boundaries.entity_parent_matching import (
    do_process_layer_files_for_parent_matching,
    do_process_layer_files_for_parent_matching_level0
)
from dashboard.tools.validate_layer_file_0 import (
    validate_layer_file_0, preprocess_layer_file_0
)
from dashboard.tools.find_country_max_level import (
    find_country_max_level
)
from dashboard.tools.admin_level_names import (
    get_admin_level_names_for_upload
)
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)
from georepo.utils.layers import get_feature_value


def read_temp_layer_file(upload_session: LayerUploadSession,
                         layer_file: LayerFile):
    """Read layer file and store to EntityTemp table."""
    level = int(layer_file.level)
    # clear existing
    existing_entities = EntityTemp.objects.filter(
        level=level,
        layer_file=layer_file,
        upload_session=upload_session
    )
    existing_entities._raw_delete(existing_entities.db)
    if not layer_file.layer_file.storage.exists(layer_file.layer_file.name):
        return
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    name_field = (
        [name_field['field'] for name_field in layer_file.name_fields
            if name_field['default']][0]
    )
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as features:
        data = []
        for feature_idx, feature in enumerate(features):
            # default code
            entity_id = get_feature_value(
                feature, id_field
            )
            # default name
            entity_name = get_feature_value(
                feature, name_field
            )
            # parent code
            feature_parent_code = None
            # find ancestor
            ancestor = None
            if level > 0:
                feature_parent_code = (
                    get_feature_value(
                        feature, layer_file.parent_id_field
                    )
                )
                if feature_parent_code:
                    if level == 1:
                        ancestor = feature_parent_code
                    else:
                        parent = EntityTemp.objects.filter(
                            upload_session=upload_session,
                            level=level - 1,
                            entity_id=feature_parent_code
                        ).first()
                        if parent:
                            ancestor = parent.ancestor_entity_id
            # add geom
            # create geometry
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            data.append(
                EntityTemp(
                    level=level,
                    layer_file=layer_file,
                    upload_session=upload_session,
                    feature_index=feature_idx,
                    entity_name=entity_name,
                    entity_id=entity_id,
                    parent_entity_id=feature_parent_code,
                    ancestor_entity_id=ancestor,
                    geometry=geom
                )
            )
            if len(data) == 5:
                EntityTemp.objects.bulk_create(data, batch_size=5)
                data.clear()
        if len(data) > 0:
            EntityTemp.objects.bulk_create(data)
        delete_tmp_shapefile(features.path)


def is_valid_upload_session(
        upload_session: LayerUploadSession,
        **kwargs) -> Tuple[bool, str]:
    """
    do pre-validation before layer upload pre-processing/prepare_validation
    Returns: IsValid, ErrorMessage
    """
    start = time.time()
    is_level0_upload = upload_session.layerfile_set.filter(
        level=0
    ).exists()
    if is_level0_upload:
        # validate no duplicate codes inside layer 0 file
        is_valid_level0_upload, duplicate = validate_layer_file_0(
            upload_session
        )
        if not is_valid_level0_upload:
            return False, (
                'There are duplicate admin level 0 geometries '
                f'with default ID: {duplicate}'
            )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.is_valid_upload_session',
            end - start)
    return True, None


def prepare_validation(
    upload_session: LayerUploadSession,
    **kwargs):
    """
    Prepare validation at step 3
    - Pre-process layer file level 0
    - Automatic parent matching for adm level 1
    - Populate admin level names
    - Populate country max level
    """
    start = time.time()
    # remove existing entity uploads
    uploads = upload_session.entityuploadstatus_set.all()
    for upload in uploads:
        # delete revised entity level 0
        if upload.revised_geographical_entity:
            upload.revised_geographical_entity.delete()
    uploads.delete()
    # set status to PRE_PROCESSING
    upload_session.auto_matched_parent_ready = False
    upload_session.status = PRE_PROCESSING
    upload_session.progress = ''
    upload_session.save(update_fields=['auto_matched_parent_ready',
                                       'status', 'progress'])
    layer_files = upload_session.layerfile_set.all()
    for layer_file in layer_files:
        read_temp_layer_file(upload_session, layer_file)
    # check if upload from level 0
    is_level0_upload = upload_session.layerfile_set.filter(
        level=0
    ).exists()
    has_level1_upload = upload_session.layerfile_set.filter(
        level=1
    ).exists()
    entity_uploads = []
    if is_level0_upload:
        # pre-process level0
        entity_uploads = preprocess_layer_file_0(
            upload_session,
            **kwargs
        )
        # do parent matching for level0
        if has_level1_upload:
            do_process_layer_files_for_parent_matching_level0(
                upload_session,
                entity_uploads,
                **kwargs
            )
    else:
        # run automatic matching parent
        entity_uploads = do_process_layer_files_for_parent_matching(
            upload_session,
            **kwargs
        )
    for entity_upload in entity_uploads:
        adm_level_names = get_admin_level_names_for_upload(
            upload_session.dataset,
            entity_upload.original_geographical_entity
        )
        entity_upload.admin_level_names = adm_level_names
        entity_upload.save()
    # find max level for each country
    find_country_max_level(
        upload_session,
        is_level0_upload,
        **kwargs
    )
    # set status back to Pending once finished
    upload_session.auto_matched_parent_ready = True
    upload_session.status = PENDING
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status'])

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.prepare_validation',
            end - start
        )


def reset_preprocessing(
    upload_session: LayerUploadSession,
    **kwargs):
    """
    Remove entity uploads
    """
    start = time.time()
    if upload_session.task_id:
        # if there is task_id then stop it first
        app.control.revoke(
            upload_session.task_id,
            terminate=True,
            signal='SIGKILL'
        )
    uploads = upload_session.entityuploadstatus_set.all()
    for upload in uploads:
        # delete revised entity level 0
        if upload.revised_geographical_entity:
            upload.revised_geographical_entity.delete()
    uploads.delete()
    # delete temp entities
    existing_entities = EntityTemp.objects.filter(
        upload_session=upload_session
    )
    existing_entities._raw_delete(existing_entities.db)
    upload_session.auto_matched_parent_ready = False
    upload_session.status = PENDING
    upload_session.task_id = ''
    upload_session.current_process = None
    upload_session.current_process_uuid = None
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status',
                                       'current_process', 'task_id',
                                       'current_process_uuid'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.reset_preprocessing',
            end - start)
