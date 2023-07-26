from django.db.models import Q
from core.models.preferences import SitePreferences
from georepo.models.dataset import Dataset, DatasetAdminLevelName
from georepo.models.entity import GeographicalEntity


def get_admin_level_names_for_upload(
        dataset: Dataset,
        prev_ancestor: GeographicalEntity):
    """
    Return admin level names for current upload
    Try to fetch from prev version in dataset
    If not exists, then use default dataset config
    """
    if prev_ancestor:
        return fetch_dataset_admin_level_names_prev_revision(
            dataset,
            prev_ancestor
        )
    return fetch_default_dataset_admin_level_names(dataset)


def fetch_default_dataset_admin_level_names(dataset: Dataset):
    names = DatasetAdminLevelName.objects.filter(
        dataset=dataset
    ).order_by('level')
    results = {}
    for name in names:
        results[name.level] = name.label
    return results


def fetch_dataset_admin_level_names_prev_revision(
        dataset: Dataset,
        prev_ancestor: GeographicalEntity):
    prev_entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        revision_number=prev_ancestor.revision_number,
        is_approved=True
    ).filter(
        Q(ancestor=prev_ancestor) | Q(id=prev_ancestor.id)
    ).exclude(
        Q(admin_level_name__isnull=True) |
        Q(admin_level_name='')
    ).order_by('level').values('level', 'admin_level_name').distinct()
    results = fetch_default_dataset_admin_level_names(dataset)
    if prev_entities:
        for prev in prev_entities:
            results[prev['level']] = prev['admin_level_name']
    return results


def populate_default_dataset_admin_level_names(dataset: Dataset):
    """
    Populate from admin level 1-6 with empty names
    """
    template = SitePreferences.preferences().level_names_template
    level_names = dataset.datasetadminlevelname_set.all()
    level_names.delete()
    for level_name in template:
        DatasetAdminLevelName.objects.create(
            dataset=dataset,
            level=level_name['level'],
            label=level_name['label']
        )
