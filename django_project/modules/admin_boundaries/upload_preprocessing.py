from typing import Tuple
from core.celery import app
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PRE_PROCESSING, PENDING
)
from modules.admin_boundaries.entity_parent_matching import (
    do_process_layer_files_for_parent_matching,
    do_process_layer_files_for_parent_matching_level0
)
from dashboard.tools.validate_layer_file_0 import (
    validate_layer_file_0, preprocess_layer_file_0,
    remove_temp_admin_level_0
)
from dashboard.tools.find_country_max_level import (
    find_country_max_level
)
from dashboard.tools.admin_level_names import (
    get_admin_level_names_for_upload
)


def is_valid_upload_session(
        upload_session: LayerUploadSession) -> Tuple[bool, str]:
    """
    do pre-validation before layer upload pre-processing/prepare_validation
    Returns: IsValid, ErrorMessage
    """
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
                'There are duplicate admin level 0 '
                f'with default code {duplicate}'
            )
    return True, None


def prepare_validation(upload_session: LayerUploadSession):
    """
    Prepare validation at step 3
    - Pre-process layer file level 0
    - Automatic parent matching for adm level 1
    - Populate admin level names
    - Populate country max level
    """
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
            create_temp_entity_level0=has_level1_upload
        )
        # do parent matching for level0
        if has_level1_upload:
            do_process_layer_files_for_parent_matching_level0(upload_session,
                                                              entity_uploads)
            remove_temp_admin_level_0(upload_session)
    else:
        # run automatic matching parent
        entity_uploads = do_process_layer_files_for_parent_matching(
            upload_session
        )
    for entity_upload in entity_uploads:
        adm_level_names = get_admin_level_names_for_upload(
            upload_session.dataset,
            entity_upload.original_geographical_entity
        )
        entity_upload.admin_level_names = adm_level_names
        entity_upload.save()
    # find max level for each country
    find_country_max_level(upload_session, is_level0_upload)
    # set status back to Pending once finished
    upload_session.auto_matched_parent_ready = True
    upload_session.status = PENDING
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status'])


def reset_preprocessing(upload_session: LayerUploadSession):
    """
    Remove entity uploads
    """
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
    # delete temporary entities from layer file (if any)
    # this may be generated from parent matching in upload level 0
    remove_temp_admin_level_0(upload_session)
    upload_session.auto_matched_parent_ready = False
    upload_session.status = PENDING
    upload_session.task_id = ''
    upload_session.save(update_fields=['auto_matched_parent_ready', 'status'])
