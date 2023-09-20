from georepo.models.dataset import Dataset
from dashboard.models.layer_upload_session import LayerUploadSession


def vector_tile_geometry_type():
    """Return geometry type in this module."""
    # return empty so tegola will infer the type from table
    return ''


def generate_adm0_default_views(dataset: Dataset):
    # no adm0 default views for boundary lines
    pass


def check_ongoing_step(upload_session: LayerUploadSession,
                       session_state: dict):
    ongoing_step = -1
    if session_state['is_in_progress']:
        ongoing_step = 3
    return ongoing_step


def check_can_update_step(upload_session: LayerUploadSession, step: int,
                          session_state: dict):
    if step == 3:
        return not session_state['is_read_only']
    return (
        not session_state['is_read_only'] and
        not session_state['is_in_progress'] and
        not session_state['has_any_result']
    )
