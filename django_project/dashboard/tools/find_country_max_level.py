import logging
import time
from dashboard.models.layer_upload_session import (
    LayerUploadSession
)
from dashboard.models.entity_upload import (
    EntityTemp
)


logger = logging.getLogger(__name__)


def find_country_max_level(
    upload_session: LayerUploadSession,
    is_level0_upload: bool,
    **kwargs
):
    """
    From each country/entity upload at upload_session,
    find maximum level of layer file that has entity at that level.

    Using EntityTemp, this process should be done after parent matching.
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
    upload_session.progress = (
        f'Processing admin level {0 if is_level0_upload else 1}'
        f'entities (0/{len(uploads)})'
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
        level_found = -1
        temp_entity = EntityTemp.objects.filter(
            upload_session=upload_session,
            ancestor_entity_id=parent_code
        ).values('level').order_by('level').distinct().last()
        if temp_entity:
            level_found = temp_entity['level']
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
