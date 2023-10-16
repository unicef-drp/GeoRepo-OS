import time
from typing import Tuple
from django.db.models import IntegerField
from django.db.models.functions import Cast
from core.celery import app
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PRE_PROCESSING, PENDING, CANCELED
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
    fetch_default_dataset_admin_level_names,
    fetch_dataset_admin_level_names_prev_revision
)
from georepo.utils.layers import read_temp_layer_file


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
    layer_files = LayerFile.objects.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(
        layer_upload_session=upload_session
    ).order_by('level_int')
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
    default_adm_level_names = fetch_default_dataset_admin_level_names(
        upload_session.dataset
    )
    for entity_upload in entity_uploads:
        if entity_upload.original_geographical_entity:
            entity_upload.admin_level_names = (
                fetch_dataset_admin_level_names_prev_revision(
                    upload_session.dataset,
                    entity_upload.original_geographical_entity
                )
            )
        else:
            entity_upload.admin_level_names = default_adm_level_names        
        entity_upload.save(update_fields=['admin_level_names'])
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
    if upload_session.status != CANCELED:
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
