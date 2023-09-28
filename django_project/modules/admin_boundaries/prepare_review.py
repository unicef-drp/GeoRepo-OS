import logging
from dashboard.models.layer_upload_session import LayerUploadSession
from dashboard.models.entity_upload import (
    EntityUploadStatus, REVIEWING,
    EntityTemp
)
from modules.admin_boundaries.admin_boundary_matching import (
    AdminBoundaryMatching
)

logger = logging.getLogger(__name__)


def ready_to_review(entity_uploads):
    """Update entity_uploads to REVIEWING."""
    # when ready to review, we can clear temp entities in current session
    upload: EntityUploadStatus = entity_uploads.first()
    if upload:
        upload_session: LayerUploadSession = upload.upload_session
        existing_entities = EntityTemp.objects.filter(
            upload_session=upload_session
        )
        existing_entities._raw_delete(existing_entities.db)
    entity_uploads.update(
        status=REVIEWING,
        progress='Pending Boundary Matching',
        comparison_data_ready=False
    )


def prepare_review(entity_upload: EntityUploadStatus, **kwargs):
    """Run boundary matching."""
    logger.info('prepare for review of admin_boundaries')
    admin_boundary_matching = (
        AdminBoundaryMatching(
            entity_upload=entity_upload,
            **kwargs
        )
    )
    admin_boundary_matching.run()
