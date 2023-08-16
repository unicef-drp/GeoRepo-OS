from django.db.models import Q, QuerySet
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from georepo.utils.dataset_view import (
    generate_default_view_adm0_latest,
    generate_default_view_adm0_all_versions,
    trigger_generate_vector_tile_for_view
)
from dashboard.models.layer_upload_session import (
    LayerUploadSession,
    PRE_PROCESSING
)
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    STARTED,
    PROCESSING
)


def vector_tile_geometry_type():
    """Return geometry type in this module."""
    return 'MultiPolygon'


def generate_adm0_default_views(dataset: Dataset):
    views = generate_default_view_adm0_latest(dataset)
    for view in views:
        trigger_generate_vector_tile_for_view(view)
    views = generate_default_view_adm0_all_versions(dataset)
    for view in views:
        trigger_generate_vector_tile_for_view(view)


def check_ongoing_step(upload_session: LayerUploadSession):
    ongoing_uploads = EntityUploadStatus.objects.filter(
        upload_session=upload_session
    ).filter(Q(status=STARTED) | Q(status=PROCESSING))
    ongoing_step = -1
    if upload_session.status == PRE_PROCESSING:
        ongoing_step = 3
    elif ongoing_uploads.exists():
        ongoing_step = 4
    return ongoing_step


def check_can_update_step(upload_session: LayerUploadSession, step: int):
    if step == 4:
        # always be able to update to last step
        return not upload_session.is_read_only()
    elif step == 3:
        existing_uploads = upload_session.entityuploadstatus_set.exclude(
            status=''
        )
        # check if no result upload from step 4
        return (
            not upload_session.is_read_only() and
            not existing_uploads.exists()
        )
    return (
        not upload_session.is_read_only() and
        not upload_session.is_in_progress() and
        not upload_session.has_any_result()
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
