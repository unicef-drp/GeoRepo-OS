import logging
import time

from dashboard.models.layer_upload_session import (
    LayerUploadSession
)
from dashboard.models.entity_upload import (
    EntityUploadChildLv1
)
from georepo.validation.layer_validation import (
    validate_level_country,
    validate_level_admin_1,
    read_layer_files
)

logger = logging.getLogger(__name__)


def find_country_max_level(
    upload_session: LayerUploadSession,
    is_level0_upload: bool,
    **kwargs
):
    """
    From each country/entity upload at upload_session,
    find maximum level of layer file that has entity at that level
    """
    start = time.time()
    available_levels = (
        upload_session.layerfile_set.values_list(
            'level', flat=True
        ).order_by('-level')
    )
    default_max_level = (
        int(available_levels[0]) if available_levels else -1
    )
    uploads = upload_session.entityuploadstatus_set.all()
    if default_max_level == -1:
        uploads.update(
            max_level_in_layer='0'
        )
        return
    default_min_level = (
        int(available_levels[len(available_levels) - 1])
        if available_levels else -1
    )
    if default_min_level == -1:
        default_min_level = 0 if is_level0_upload else 1
    layer_cache = read_layer_files(upload_session.layerfile_set.all())
    upload_session.progress = (
        f'Processing admin level 0 entities (0/{len(uploads)})'
    )
    logger.info(upload_session.progress)
    upload_session.save(update_fields=['progress'])
    for upload_idx, upload in enumerate(uploads):
        # find parent code
        parent_code = (
            upload.original_geographical_entity.internal_code
            if upload.original_geographical_entity
            else upload.revised_entity_id
        )
        # find level1_children and check whether has rematched parent
        # if rematched, then validation will be using different func
        level1_children = EntityUploadChildLv1.objects.filter(
            entity_upload=upload
        )
        level1_codes = level1_children.values_list(
            'entity_id', flat=True
        )
        has_rematched_children = level1_children.filter(
            is_parent_rematched=True
        ).exists()
        level_found = -1
        for level in range(default_max_level, 0, -1):
            if has_rematched_children:
                # rematched_children means
                # layer0_id (default code ori entity) <>
                #   parent_code in layer file
                has_valid_level = validate_level_admin_1(
                    upload_session,
                    level1_codes,
                    level,
                    layer_cache,
                    **kwargs
                )
                if has_valid_level:
                    level_found = level
                    break
            else:
                has_valid_level = validate_level_country(
                    upload_session,
                    parent_code,
                    level,
                    layer_cache,
                    **kwargs
                )
                if has_valid_level:
                    level_found = level
                    break
        upload.max_level_in_layer = (
            str(level_found) if level_found != -1
            else str(default_min_level)
        )
        upload.save(update_fields=['max_level_in_layer'])
        upload_session.progress = (
            f'Processing admin level {0 if is_level0_upload else 1} '
            f'entities ({upload_idx+1}/{len(uploads)})'
        )
        logger.info(upload_session.progress)
        upload_session.save(update_fields=['progress'])

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('find_country_max_level', end - start)
