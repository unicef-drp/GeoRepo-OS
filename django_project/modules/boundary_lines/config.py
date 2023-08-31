from django.db.models import Q
from georepo.models.dataset import Dataset
from dashboard.models.layer_upload_session import LayerUploadSession
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    STARTED,
    PROCESSING
)


def vector_tile_geometry_type():
    """Return geometry type in this module."""
    # return empty so tegola will infer the type from table
    return ''


def generate_adm0_default_views(dataset: Dataset):
    # no adm0 default views for boundary lines
    pass


def check_ongoing_step(upload_session: LayerUploadSession):
    ongoing_uploads = EntityUploadStatus.objects.filter(
        upload_session=upload_session
    ).filter(Q(status=STARTED) | Q(status=PROCESSING))
    ongoing_step = -1
    if ongoing_uploads.exists():
        ongoing_step = 3
    return ongoing_step


def check_can_update_step(upload_session: LayerUploadSession, step: int):
    if step == 3:
        return not upload_session.is_read_only()
    return (
        not upload_session.is_read_only() and
        not upload_session.is_in_progress() and
        not upload_session.has_any_result()
    )
