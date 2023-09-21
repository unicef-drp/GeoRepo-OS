import datetime
import time

from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from dashboard.models.entity_upload import (
    EntityUploadStatus, REJECTED, APPROVED
)
from dashboard.models.layer_upload_session import (
    DONE
)
from dashboard.models.layer_file import LayerFile
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    generate_default_view_dataset_all_versions
)
from georepo.utils.dataset_view import trigger_generate_dynamic_views
from georepo.utils.unique_code import (
    generate_concept_ucode
)


def reject_revision(entity_upload: EntityUploadStatus):
    """
    Reject revision and will delete the rejected entities
    """
    entity_upload.status = REJECTED
    entity_upload.save()

    entity_upload.upload_session.status = DONE
    entity_upload.upload_session.save()

    # Delete new entities after rejected
    layer_files = LayerFile.objects.filter(
        layer_upload_session=entity_upload.upload_session
    )
    GeographicalEntity.objects.filter(
        layer_file__in=layer_files
    ).delete()


def approve_revision(
    entity_upload: EntityUploadStatus,
    user,
    is_batch=False,
    **kwargs
):
    """
    Approve revision.

    This will be run as background task.
    """
    start = time.time()
    # generate concept unique code
    ancestor_entity = entity_upload.revised_geographical_entity
    new_entities = GeographicalEntity.objects.filter(
        layer_file__in=entity_upload
        .upload_session.layerfile_set.all()
    ).order_by('internal_code')
    generate_concept_ucode(ancestor_entity, new_entities, False)
    if entity_upload.upload_session.is_historical_upload:
        approve_historical_upload(entity_upload, user)
    else:
        approve_new_revision_upload(entity_upload, user)
    dataset = entity_upload.upload_session.dataset
    # generate default views
    generate_default_views(dataset)
    # change status to APPROVED
    entity_upload.status = APPROVED
    entity_upload.save()

    entity_upload.upload_session.status = DONE
    entity_upload.upload_session.save()
    if not is_batch:
        # trigger refresh views
        trigger_generate_dynamic_views(dataset)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('approve_revision', end - start)

def generate_default_views(dataset: Dataset):
    generate_default_view_dataset_latest(dataset)
    generate_default_view_dataset_all_versions(dataset)


def approve_new_revision_upload(entity_upload: EntityUploadStatus, user):
    dataset = entity_upload.upload_session.dataset
    # Set is_latest to false for all old entities
    old_entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        revision_number=entity_upload.revision_number - 1
    )
    # update end_date for old entities
    old_entities.update(
        is_latest=False,
        end_date=entity_upload.upload_session.started_at
    )

    # Set is_latest to true for all new entities
    layer_files = LayerFile.objects.filter(
        layer_upload_session=entity_upload.upload_session
    )
    new_entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        layer_file__in=layer_files
    )
    new_entities.update(
        is_latest=True,
        is_approved=True,
        approved_date=datetime.datetime.now(),
        approved_by=user
    )


def approve_historical_upload(entity_upload: EntityUploadStatus, user):
    dataset = entity_upload.upload_session.dataset
    start_date = (
        entity_upload.upload_session.historical_start_date
    )
    end_date = (
        entity_upload.upload_session.historical_end_date
    )
    # update end_date of prev version (before start_date of historical upload)
    previous_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        start_date__lt=start_date,
        is_approved=True
    ).order_by('start_date').last()
    if previous_entity:
        previous_unique_code_version = previous_entity.unique_code_version
        previous_entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            unique_code_version=previous_unique_code_version
        )
        previous_entities.update(
            end_date=start_date
        )
    # update start_date of next version (after end_date of historical upload)
    next_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        start_date__gt=start_date,
        is_approved=True
    ).order_by('start_date').first()
    if next_entity:
        next_unique_code_version = next_entity.unique_code_version
        next_entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            unique_code_version=next_unique_code_version
        )
        next_entities.update(
            start_date=end_date
        )
    # update new entities with is_approved=True
    layer_files = LayerFile.objects.filter(
        layer_upload_session=entity_upload.upload_session
    )
    new_entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        layer_file__in=layer_files
    )
    new_entities.update(
        is_approved=True,
        approved_date=datetime.datetime.now(),
        approved_by=user
    )
