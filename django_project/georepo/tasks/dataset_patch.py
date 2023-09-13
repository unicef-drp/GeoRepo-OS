from celery import shared_task
import uuid
import logging
from django.db.models import Q
from georepo.models.entity import GeographicalEntity
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.utils.unique_code import generate_concept_ucode_base
from georepo.utils.dataset_view import (
    calculate_entity_count_in_view,
    init_view_privacy_level,
    generate_view_bbox
)

logger = logging.getLogger(__name__)


@shared_task(name="dataset_patch")
def dataset_patch(dataset_id):
    from django.db.models import Max
    from georepo.models.dataset import (
        Dataset
    )
    from georepo.models.entity import (
        GeographicalEntity
    )
    from georepo.utils.unique_code import (
        generate_unique_code
    )
    dataset = Dataset.objects.get(id=dataset_id)
    # check if dataset has empty max revision number
    max_rev_number = GeographicalEntity.objects.filter(
        dataset=dataset
    ).aggregate(Max('revision_number'))
    if not max_rev_number['revision_number__max']:
        print(f'Updating revision number of {dataset.label} to 1')
        GeographicalEntity.objects.filter(
            dataset=dataset
        ).update(revision_number=1)

    # fix empty start date
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        start_date__isnull=True
    ).order_by('id')
    print(
        f'Fixing empty start-date {entities.count()} '
        f'in dataset {dataset.label}'
    )
    entities.update(
        start_date=dataset.created_at
    )
    # fix unicode
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0
    ).order_by('id')
    print(
        f'Fixing empty unicode {entities.count()} '
        f'in dataset {dataset.label}'
    )
    for ancestor in entities:
        all_children = ancestor.all_children().order_by(
            'level', 'label'
        )
        total_count = all_children.count()
        all_children.update(unique_code='')
        count = 0
        for geo_entity in all_children:
            generate_unique_code(geo_entity)
            count += 1
            if count % 100 == 0:
                print(
                    f'Updated {ancestor.internal_code} - '
                    f'{count}/{total_count} records'
                )
    # fix unicode version
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0
    ).order_by('id')
    print(
        f'Fixing empty unicode version {entities.count()} '
        f'in dataset {dataset.label}'
    )
    for ancestor in entities:
        all_children = ancestor.all_children().order_by(
            'level', 'label'
        )
        total_count = all_children.count()
        all_children.update(unique_code_version=None)
        count = 0
        for geo_entity in all_children:
            # generate_unique_code_version(geo_entity)
            count += 1
            if count % 100 == 0:
                print(
                    f'Updated {ancestor.internal_code} - '
                    f'{count}/{total_count} records'
                )


def dataset_patch_is_latest(dataset_id, revision_number):
    from georepo.models.dataset import (
        Dataset
    )
    from georepo.models.entity import (
        GeographicalEntity
    )
    dataset = Dataset.objects.get(id=dataset_id)
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        revision_number=revision_number
    )
    print(
        f'Fixing is_latest and is_approved {entities.count()} '
        f'in dataset {dataset.label} for revision {revision_number}'
    )
    entities.update(
        is_latest=True,
        is_approved=True
    )


def patch_revision_uuid(dataset_id):
    entities = GeographicalEntity.objects.filter(
        dataset_id=dataset_id
    )
    print(f'Total entities of dataset-{dataset_id}: {entities.count()}')
    entities = entities.values_list('id', flat=True)
    idx = 0
    for entityId in entities:
        GeographicalEntity.objects.filter(
            id=entityId
        ).update(uuid_revision=uuid.uuid4())
        idx += 1
        if idx % 1000 == 0:
            print(f'Total count {idx}')


@shared_task(name='generate_concept_ucode')
def generate_concept_ucode(dataset_id):
    dataset = Dataset.objects.get(id=dataset_id)
    adm0_entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        is_approved=True,
        level=0
    ).order_by('unique_code').values_list('unique_code', flat=True).distinct()
    for adm0 in adm0_entities:
        revision_numbers = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
        ).filter(
            Q(
                Q(ancestor__isnull=True) &
                Q(unique_code=adm0)
            ) |
            Q(
                Q(ancestor__isnull=False) &
                Q(ancestor__unique_code=adm0)
            )
        ).order_by(
            'revision_number'
        ).values_list('revision_number', flat=True).distinct()
        sequence = 1
        for revision in revision_numbers:
            entities = GeographicalEntity.objects.filter(
                dataset=dataset,
                is_approved=True,
                revision_number=revision
            ).filter(
                Q(
                    Q(ancestor__isnull=True) &
                    Q(unique_code=adm0)
                ) |
                Q(
                    Q(ancestor__isnull=False) &
                    Q(ancestor__unique_code=adm0)
                )
            ).filter(
                Q(concept_ucode__isnull=True) |
                Q(concept_ucode='')
            ).order_by('level', 'internal_code').iterator(
                chunk_size=1
            )
            for entity in entities:
                cucode = generate_concept_ucode_base(entity, sequence)
                GeographicalEntity.objects.filter(
                    uuid=entity.uuid,
                    dataset=dataset,
                    is_approved=True,
                ).update(concept_ucode=cucode)
                sequence += 1


@shared_task(name='dataset_patch_views')
def dataset_patch_views(dataset_id):
    dataset = Dataset.objects.get(id=dataset_id)
    views = DatasetView.objects.filter(
        dataset=dataset
    )
    for view in views:
        logger.info(f'Patch view {view}')
        init_view_privacy_level(view)
        calculate_entity_count_in_view(view)
        generate_view_bbox(view)
        logger.info(f'Patch view {view} is finished')
    logger.info(f'Patch views in dataset {dataset} is finished')
