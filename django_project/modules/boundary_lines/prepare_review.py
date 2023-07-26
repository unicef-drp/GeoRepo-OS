import logging
from django.db.models import Count
from georepo.models.boundary_type import BoundaryType
from georepo.models.entity import GeographicalEntity
from dashboard.models.entity_upload import (
    EntityUploadStatus, REVIEWING
)
from dashboard.models.layer_file import LayerFile


logger = logging.getLogger(__name__)


class BoundaryLinesSummaryData(object):
    def __init__(self,
                 boundary_type: str,
                 boundary_type_label: str,
                 count: int):
        self.boundary_type = boundary_type
        self.boundary_type_label = boundary_type_label
        self.count = count


def ready_to_review(entity_uploads):
    """Update entity_uploads to REVIEWING."""
    entity_uploads.update(
        status=REVIEWING,
        progress=''
    )


def prepare_review(entity_upload: EntityUploadStatus):
    logger.info('prepare for review of boundary_lines')
    layer_files = LayerFile.objects.filter(
        layer_upload_session=entity_upload.upload_session
    ).order_by('level')
    entity_types = GeographicalEntity.objects.filter(
        layer_file__in=layer_files
    ).values('type').annotate(total=Count('type')).order_by('-total')
    dataset = entity_upload.upload_session.dataset
    summary_data = []
    for entity_type in entity_types:
        boundary_type = BoundaryType.objects.filter(
            type=entity_type['type'],
            dataset=dataset
        ).first()
        if boundary_type:
            summary_data.append(
                vars(BoundaryLinesSummaryData(
                    boundary_type=boundary_type.value,
                    boundary_type_label=boundary_type.type.label,
                    count=entity_type['total']
                ))
            )
        else:
            summary_data.append(
                vars(BoundaryLinesSummaryData(
                    boundary_type='NA',
                    boundary_type_label='NA',
                    count=entity_type['total']
                ))
            )
    entity_upload.comparison_data_ready = True
    entity_upload.boundary_comparison_summary = (
        summary_data
    )
    entity_upload.save()
