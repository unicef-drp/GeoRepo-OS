from django.db.models import QuerySet
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.utils.dataset_view import (
    generate_default_view_adm0_latest,
    generate_default_view_adm0_all_versions,
    init_view_privacy_level
)
from dashboard.models.layer_upload_session import (
    LayerUploadSession,
    PRE_PROCESSING,
    UPLOAD_PROCESS_COUNTRIES_SELECTION
)


def vector_tile_geometry_type():
    """Return geometry type in this module."""
    return 'MultiPolygon'


def generate_adm0_default_views(dataset: Dataset):
    views = generate_default_view_adm0_latest(dataset)
    for view in views:
        # update max and min privacy level of entities in view
        init_view_privacy_level(view)
    views = generate_default_view_adm0_all_versions(dataset)
    for view in views:
        # update max and min privacy level of entities in view
        init_view_privacy_level(view)


def check_ongoing_step(upload_session: LayerUploadSession,
                       session_state: dict):
    ongoing_step = -1
    if upload_session.status == PRE_PROCESSING:
        ongoing_step = 3
    elif session_state['is_in_progress']:
        if (
            upload_session.
            current_process == UPLOAD_PROCESS_COUNTRIES_SELECTION
        ):
            ongoing_step = 3
        else:
            ongoing_step = 4
    return ongoing_step


def check_can_update_step(upload_session: LayerUploadSession, step: int,
                          session_state: dict):
    if step == 4:
        # always be able to update to last step
        return not session_state['is_read_only']
    elif step == 3:
        existing_uploads = upload_session.entityuploadstatus_set.exclude(
            status=''
        )
        # check if no result upload from step 4
        return (
            not session_state['is_read_only'] and
            not existing_uploads.exists()
        )
    return (
        not session_state['is_read_only'] and
        not session_state['is_in_progress'] and
        not session_state['has_any_result']
    )


def get_new_entities_in_upload(entity_upload) -> QuerySet[GeographicalEntity]:
    """Return new entities query set ordered by level and defaultCode."""
    if entity_upload.revised_geographical_entity is None:
        return QuerySet.none()
    return (
        entity_upload.revised_geographical_entity.
        all_children().filter(
            layer_file__in=entity_upload.upload_session.
            layerfile_set.all(),
        ).order_by('level', 'internal_code')
    )
