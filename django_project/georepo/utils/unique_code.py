from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from core.models.preferences import SitePreferences
from django.db.models import Max, Count, Q, QuerySet


"""
Pattern for generating new IDs:
ISO3_0001_0001_V01, e.g. AGO_0001_0010_V01
    AGO_0001_V01
    AGO_0001_0001_V01
    AGO_0001_0002_V01
"""
"""
Updated Pattern UniqueCode with dataset's shortcode
e.g. ABC_AGO_0001_0010_V01
Applicable only to shortcode <> OAB (Admin Boundaries)
"""


def get_unique_code_prefix(dataset: Dataset, level: int) -> str:
    """Get prefix shortcode from dataset."""
    exclusion = SitePreferences.preferences().short_code_exclusion
    if exclusion:
        exclusion = exclusion.split(',')
    return (
        f'{dataset.short_code}_'
        if dataset.short_code and dataset.short_code not in exclusion and
        level == 0
        else ''
    )


def generate_unique_code_base(entity: GeographicalEntity,
                              parent_unique_code: str,
                              sequence_number: str) -> str:
    """Generate unique code base."""
    if parent_unique_code is None or parent_unique_code == '':
        # generate without parent unique code
        return (
            f'{get_unique_code_prefix(entity.dataset, entity.level)}'
            f'{entity.internal_code}'
        )
    return (
        f'{get_unique_code_prefix(entity.dataset, entity.level)}'
        f'{parent_unique_code}_'
        f'{sequence_number}'
    )


def generate_concept_ucode_base(entity: GeographicalEntity,
                                sequence_number: str) -> str:
    """Generate concept unique code, pattern: #shortCode_PAK_1."""
    """TODO: confirm how to generate for boundary lines"""
    prefix = get_unique_code_prefix(entity.dataset, 0)
    if entity.level == 0:
        return (
            f'#{prefix}{entity.internal_code}_{sequence_number}'
        )
    if not entity.ancestor:
        raise ValueError('Entity does not have ancestor!')
    return (
        f'#{prefix}{entity.ancestor.internal_code}_{sequence_number}'
    )


def generate_unique_code(
        geographical_entity: GeographicalEntity) -> GeographicalEntity:
    """
    Generate unique code for a geographical entity.

    :param geographical_entity: GeographicalEntity object
    :return update geographical entity with unique coded
    """
    if geographical_entity.parent:
        parent = geographical_entity.parent
        if not parent.unique_code:
            generate_unique_code(parent)
        parent_unique_code = parent.unique_code
    else:  # if parent has empty unique code
        if not geographical_entity.unique_code:
            if geographical_entity.internal_code:
                geographical_entity.unique_code = generate_unique_code_base(
                    geographical_entity,
                    None,
                    None
                )
            geographical_entity.save()
        return geographical_entity
    filters = {
        'parent': parent,
        'dataset': geographical_entity.dataset,
        'level': geographical_entity.level,
        'revision_number': geographical_entity.revision_number
    }
    if geographical_entity.layer_file:
        filters['layer_file'] = geographical_entity.layer_file
    siblings = GeographicalEntity.objects.filter(
        **filters
    ).order_by('label')

    entity_index = (
        list(siblings.values_list('id', flat=True)).index(
            geographical_entity.id)
    )

    unique_code = generate_unique_code_base(
        geographical_entity,
        parent_unique_code,
        str(entity_index + 1).zfill(4)
    )

    geographical_entity.unique_code = unique_code
    geographical_entity.save()
    return geographical_entity


def generate_unique_code_version(
        entity: GeographicalEntity) -> GeographicalEntity:
    """
    Generate the version of the geographical entity
    e.g. AGO_0001_V100 => V100 is the version
    ***Deprecated***
    ***This may generate different version in same upload***
    :param entity: GeographicalEntity object
    """
    if entity.unique_code_version:
        return entity

    current_version = 1
    # Find entity started after the current entity
    next_entity = GeographicalEntity.objects.filter(
        dataset=entity.dataset,
        unique_code=entity.unique_code,
        start_date__gt=entity.start_date
    ).order_by('start_date').first()

    previous_entity = GeographicalEntity.objects.filter(
        dataset=entity.dataset,
        unique_code=entity.unique_code,
        start_date__lt=entity.start_date
    ).order_by('start_date').last()

    if (
        next_entity and not next_entity.unique_code_version
    ):
        next_entity = None

    if (
        previous_entity and not
            previous_entity.unique_code_version):
        generate_unique_code_version(previous_entity)

    # Entity added before the first entity
    # e.g. first entity = 1, current version = 0.5
    if not previous_entity and next_entity:
        if next_entity.unique_code_version:
            current_version = next_entity.unique_code_version / 2

    # Entity added after the last entity
    # e.g. last entity version => 3, current version => 3 + 1 = 4
    if previous_entity and not next_entity:
        if previous_entity.unique_code_version:
            current_version = previous_entity.unique_code_version + 1

    # Entity added between entities
    if previous_entity and next_entity:
        if (
            previous_entity.unique_code_version and
            next_entity.unique_code_version
        ):
            current_version = (
                  previous_entity.unique_code_version +
                  next_entity.unique_code_version
            ) / 2

    entity.unique_code_version = current_version
    entity.save()
    return entity


def parse_unique_code(unique_code: str):
    """
    Parse unique code with version
    E.g. AGO_0001_V100 -> AGO_0001, 100
    AGO_0001_V1.5 -> AGO_0001, 1.5
    """
    codes = unique_code.split('_')
    if len(codes) < 2:
        raise ValueError(f'Invalid ucode {unique_code}')
    version = codes[-1]
    if not version.startswith('V'):
        raise ValueError(f'Invalid ucode {unique_code}')
    ucode = unique_code.replace(f'_{version}', '')
    version = version.replace('V', '', 1)
    return ucode, float(version)


def get_version_code(version: float) -> str:
    """
    Convert version number to string
    """
    version_code = f'{version:.4f}' if version else '1'
    while '.' in version_code and (
        version_code[-1] in ['.', '0']
    ):
        version_code = version_code[:-1]
    return version_code


def get_unique_code(ucode: str, version: float) -> str:
    """
    Concat ucode with version
    E.g. AGO_0001 + 1.5 -> AGO_0001_V1.5
    """
    version_code = f'V{version:.4f}' if version else 'V1'
    while '.' in version_code and (
        version_code[-1] in ['.', '0']
    ):
        version_code = version_code[:-1]
    return f'{ucode}_{version_code}'


def generate_upload_unique_code_version(
        dataset: Dataset,
        start_date,
        ancestor_entity: GeographicalEntity = None) -> float:
    """
    Generate unique_code_version for an upload
    If ancestor_entity is provided, it must have unique_code
    """
    if ancestor_entity is None:
        # if new entity level 0, then starts from 1
        return 1
    unique_code = ancestor_entity.unique_code
    # Find entity started after the current entity
    next_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        unique_code=unique_code,
        start_date__gt=start_date,
        is_approved=True
    ).order_by('start_date').first()

    previous_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        unique_code=unique_code,
        start_date__lt=start_date,
        is_approved=True
    ).order_by('start_date').last()
    current_version = 1
    # Entity added before the first entity
    # e.g. first entity = 1, current version = 0.5
    if not previous_entity and next_entity:
        if next_entity.unique_code_version:
            current_version = next_entity.unique_code_version / 2

    # Entity added after the last entity
    # e.g. last entity version => 3, current version => 3 + 1 = 4
    if previous_entity and not next_entity:
        if previous_entity.unique_code_version:
            current_version = previous_entity.unique_code_version + 1

    # Entity added between entities
    if previous_entity and next_entity:
        if (
            previous_entity.unique_code_version and
            next_entity.unique_code_version
        ):
            current_version = (
                  previous_entity.unique_code_version +
                  next_entity.unique_code_version
            ) / 2
    return current_version


def get_latest_revision_number(dataset: Dataset):
    """
    Retrieve latest upload revision number if exist
    if not, then return the maximum
    Note: if not exist, then could be from empty dataset,
    or historical uploads
    """
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_approved=True,
        is_latest=True
    )
    if entities.exists():
        return (
            entities.aggregate(Max('revision_number'))['revision_number__max']
        )
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_approved=True
    )
    if entities.exists():
        return (
            entities.aggregate(Max('revision_number'))['revision_number__max']
        )
    return 0


def generate_unique_code_from_comparison(entity: GeographicalEntity,
                                         comparison: GeographicalEntity):
    """
    Reuse unique code sequence number from comparison entity
    """
    if entity.level == 0:
        # generate level 0 without any sequence number
        entity.unique_code = generate_unique_code_base(entity, None, None)
    elif entity.level == comparison.level:
        # only reuse if in the same level and has same parent
        if (
            entity.parent and comparison.parent and
            entity.parent.unique_code == comparison.parent.unique_code
        ):
            sequence_number = comparison.unique_code.split('_')[-1]
            entity.unique_code = generate_unique_code_base(
                entity,
                entity.parent.unique_code,
                sequence_number
            )
    else:
        # comparison is in different level, we generate new unique code
        entity.unique_code = ''
    entity.save(update_fields=['unique_code'])


def count_max_unique_code(dataset: Dataset, level: int,
                          parent: GeographicalEntity,
                          unique_code_version: float = None):
    """
    Get maximum sequence number of unique code from entities in specific level
    This will count across revisions and group by concept uuid and a parent
    This function should be called for entities with level > 0

    if unique_code_version is provided, then can search in pending revision
    Example:
    Rev1: PAK_001, PAK_002, PAK_003
    Rev2: PAK_001, PAK_002, PAK_003, PAK_004
    Output = 4
    """
    if level == 0:
        return 0
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=level,
        parent__unique_code=parent.unique_code
    )
    if unique_code_version is None:
        entities = entities.filter(
            is_approved=True
        )
    else:
        # if search by unique_code_version,
        # then can search across pending revision
        entities = entities.filter(
            Q(is_approved=True) |
            (
                (Q(is_approved=False) | Q(is_approved__isnull=True)) &
                Q(unique_code_version=unique_code_version)
            )
        )
    entities = entities.aggregate(entity_count=Count('uuid', distinct=True))
    return entities['entity_count']


def generate_concept_ucode(ancestor_entity,
                           new_entities: QuerySet[GeographicalEntity],
                           use_boundary_comparison: bool = True,
                           dataset: Dataset = None):
    """Generate concept ucode to all entities inside entity_upload."""
    from dashboard.models.boundary_comparison import BoundaryComparison
    # find the number of concept uuid in current ancestor
    sequence = 0
    if ancestor_entity:
        entities = GeographicalEntity.objects.filter(
            dataset=ancestor_entity.dataset,
            is_approved=True,
        ).filter(
            Q(
                Q(ancestor__isnull=True) &
                Q(unique_code=ancestor_entity.unique_code)
            ) |
            Q(
                Q(ancestor__isnull=False) &
                Q(ancestor__unique_code=ancestor_entity.unique_code)
            )
        )
        entities = entities.aggregate(entity_count=Count('uuid', distinct=True))
        sequence = entities['entity_count']
    elif dataset:
        entities = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True,
        ).aggregate(entity_count=Count('uuid', distinct=True))
        sequence = entities['entity_count']
    entity: GeographicalEntity
    for entity in new_entities.iterator(chunk_size=1):
        if use_boundary_comparison:
            boundary_comparison = BoundaryComparison.objects.filter(
                main_boundary=entity,
            ).first()
            if not boundary_comparison:
                continue
            if (
                boundary_comparison.is_same_entity and
                boundary_comparison.comparison_boundary
            ):
                # use concept ucode from comparison
                entity.concept_ucode = (
                    boundary_comparison.comparison_boundary.concept_ucode
                )
            else:
                # generate new concept ucode
                entity.concept_ucode = generate_concept_ucode_base(
                    entity,
                    str(sequence + 1)
                )
                sequence += 1
        else:
            # generate new concept ucode
            entity.concept_ucode = generate_concept_ucode_base(
                entity,
                str(sequence + 1)
            )
            sequence += 1
        entity.save(update_fields=['concept_ucode'])
