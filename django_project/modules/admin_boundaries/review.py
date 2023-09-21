import time

from django.utils import timezone
from georepo.models.entity import GeographicalEntity
from georepo.models.dataset import Dataset
from dashboard.models.entity_upload import (
    EntityUploadStatus, REJECTED, APPROVED
)
from dashboard.models.layer_upload_session import (
    DONE, PENDING
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    generate_default_view_dataset_all_versions,
    generate_default_view_adm0_latest,
    generate_default_view_adm0_all_versions,
    trigger_generate_dynamic_views
)
from georepo.utils.unique_code import (
    generate_concept_ucode
)
from modules.admin_boundaries.config import (
    get_new_entities_in_upload
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
    new_entities = (
        entity_upload.revised_geographical_entity.all_children()
    )
    new_entities.delete()


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
    # generate concept unique code for entities in the current upload only
    ancestor_entity = entity_upload.revised_geographical_entity
    new_entities = (
        get_new_entities_in_upload(entity_upload)
    )
    generate_concept_ucode(ancestor_entity, new_entities)
    if entity_upload.upload_session.is_historical_upload:
        approve_historical_upload(
            entity_upload,
            user,
            **kwargs
        )
    else:
        approve_new_revision_upload(
            entity_upload,
            user,
            **kwargs
        )
    dataset = entity_upload.upload_session.dataset
    # generate default views
    generate_default_views(dataset)
    # change status to APPROVED
    entity_upload.status = APPROVED
    entity_upload.save()

    entity_upload.upload_session.status = DONE
    entity_upload.upload_session.save()

    dataset.is_simplified = False
    dataset.save()
    if not is_batch:
        # trigger refresh views
        trigger_generate_dynamic_views(
            dataset,
            adm0=entity_upload.revised_geographical_entity
        )


def approve_new_revision_upload(
    entity_upload: EntityUploadStatus,
    user,
    **kwargs
):
    start = time.time()
    # Set is_latest to false for all old entities
    if entity_upload.original_geographical_entity:
        old_entities = (
            entity_upload.original_geographical_entity.all_children()
        )
        # update end_date for old entities
        old_entities.update(
            is_latest=False,
            end_date=entity_upload.upload_session.started_at
        )
        # find other pending entity upload with same original id
        other_uploads = EntityUploadStatus.objects.filter(
            original_geographical_entity=(
                entity_upload.original_geographical_entity
            ),
            status__exact='',
            upload_session__status=PENDING
        ).exclude(
            id=entity_upload.id
        )
        other_uploads.update(
            original_geographical_entity=(
                entity_upload.revised_geographical_entity
            )
        )

    # Set is_latest to true for all new entities
    new_entities = (
        entity_upload.revised_geographical_entity.all_children()
    )
    new_entities.update(
        is_latest=True,
        is_approved=True,
        approved_date=timezone.now(),
        approved_by=user
    )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'approve_new_revision_upload',
            end - start
        )


def approve_historical_upload(
    entity_upload: EntityUploadStatus,
    user,
    **kwargs
):
    start = time.time()
    entity = entity_upload.revised_geographical_entity
    # update end_date of prev version (before start_date of historical upload)
    previous_entity = GeographicalEntity.objects.filter(
        dataset=entity.dataset,
        unique_code=entity.unique_code,
        start_date__lt=entity.start_date,
        is_approved=True
    ).order_by('start_date').last()
    if previous_entity:
        previous_entities = previous_entity.all_children()
        previous_entities.update(
            end_date=entity.start_date
        )
    # update start_date of next version (after end_date of historical upload)
    next_entity = GeographicalEntity.objects.filter(
        dataset=entity.dataset,
        unique_code=entity.unique_code,
        start_date__gt=entity.start_date
    ).order_by('start_date').first()
    if next_entity:
        next_entities = next_entity.all_children()
        next_entities.update(
            start_date=entity.end_date
        )
    # update new entities with is_approved=True
    new_entities = (
        entity.all_children()
    )
    new_entities.update(
        is_approved=True,
        approved_date=timezone.now(),
        approved_by=user
    )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'approve_historical_upload',
            end - start
        )


def generate_default_views(dataset: Dataset):
    generate_default_view_dataset_latest(dataset)
    generate_default_view_dataset_all_versions(dataset)
    if dataset.generate_adm0_default_views:
        generate_default_view_adm0_latest(dataset)
        generate_default_view_adm0_all_versions(dataset)
