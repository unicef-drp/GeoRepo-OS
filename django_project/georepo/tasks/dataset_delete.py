from celery import shared_task

from django.db.models import Q
from georepo.models.dataset import Dataset
from georepo.models.entity import (
    GeographicalEntity,
    EntityId,
    EntityName,
    EntitySimplified,
    EntityEditHistory
)
from dashboard.models.boundary_comparison import (
    BoundaryComparison
)
from dashboard.models.entity_upload import (
    EntityUploadStatus,
    EntityUploadChildLv1,
    EntityTemp,
    EntityUploadStatusLog
)
from dashboard.models.layer_upload_session import (
    LayerUploadSession
)
from dashboard.models.layer_file import (
    LayerFile
)


def remove_dataset_resources(dataset: Dataset):
    # delete resources from upload
    temp_entities = EntityTemp.objects.filter(
        upload_session__dataset=dataset
    )
    temp_entities._raw_delete(temp_entities.db)
    parent_matching = EntityUploadChildLv1.objects.filter(
        entity_upload__upload_session__dataset=dataset
    )
    parent_matching._raw_delete(parent_matching.db)
    logs = EntityUploadStatusLog.objects.filter(
        Q(layer_upload_session__dataset=dataset) |
        Q(entity_upload_status__upload_session__dataset=dataset)
    )
    logs._raw_delete(logs.db)
    uploads = EntityUploadStatus.objects.filter(
        upload_session__dataset=dataset)
    uploads._raw_delete(uploads.db)
    # delete entities
    simplified_entities = EntitySimplified.objects.filter(
        geographical_entity__dataset=dataset
    )
    simplified_entities._raw_delete(simplified_entities.db)
    ids = EntityId.objects.filter(
        geographical_entity__dataset=dataset
    )
    ids._raw_delete(ids.db)
    names = EntityName.objects.filter(
        geographical_entity__dataset=dataset
    )
    names._raw_delete(names.db)
    reviews = BoundaryComparison.objects.filter(
        Q(main_boundary__dataset=dataset) |
        Q(comparison_boundary__dataset=dataset)
    )
    reviews._raw_delete(reviews.db)
    # delete entity edit history
    history = EntityEditHistory.objects.filter(
        geographical_entity__dataset=dataset
    )
    history._raw_delete(history.db)
    entities = GeographicalEntity.objects.filter(
        dataset=dataset
    )
    entities._raw_delete(entities.db)
    # delete layer files and upload sessions
    layer_files = LayerFile.objects.filter(
        layer_upload_session__dataset=dataset
    )
    for layer_file in layer_files:
        if layer_file.layer_file:
            if (
                not layer_file.layer_file.storage.exists(
                    layer_file.layer_file.name)
            ):
                layer_file.layer_file = None
                layer_file.save(update_fields=['layer_file'])
    LayerUploadSession.objects.filter(
        dataset=dataset
    ).delete()


@shared_task(name="dataset_delete")
def dataset_delete(dataset_ids):
    for dataset in Dataset.objects.filter(id__in=dataset_ids):
        remove_dataset_resources(dataset)
        dataset.delete()
