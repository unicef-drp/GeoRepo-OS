import re
from enum import Enum
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission
from rest_framework.authtoken.models import Token
from guardian.shortcuts import get_objects_for_user, assign_perm,\
    remove_perm
from guardian.core import ObjectPermissionChecker
from core.models.preferences import SitePreferences
from georepo.models import Module, Dataset, DatasetView


User = get_user_model()

MAX_PRIVACY_LEVEL = 4
MIN_PRIVACY_LEVEL = 1

User = get_user_model()


# Permission List
class PermissionType(Enum):
    OWN_PERMISSION = 'Own'
    MANAGE_PERMISSION = 'Manage'
    WRITE_PERMISSION = 'Write'
    READ_PERMISSION = 'Read'

    @classmethod
    def get_max_permission_for_module(cls, obj,
                                      checker: ObjectPermissionChecker):
        # check can write
        if checker.has_perm('module_add_dataset', obj):
            return cls.WRITE_PERMISSION
        return None

    @classmethod
    def get_max_permission_for_dataset(cls, obj,
                                       checker: ObjectPermissionChecker):
        # check owner
        if checker.has_perm('delete_dataset', obj):
            return cls.OWN_PERMISSION
        # check manager
        if (
            checker.has_perm('dataset_add_view', obj)
        ):
            return cls.MANAGE_PERMISSION
        # check writer
        if (
            checker.has_perm('review_upload', obj) or
            checker.has_perm('upload_data', obj)
        ):
            return cls.WRITE_PERMISSION

        return cls.READ_PERMISSION

    @classmethod
    def get_max_permission_for_datasetview(cls, obj,
                                           checker: ObjectPermissionChecker):
        # check owner
        if checker.has_perm('delete_datasetview', obj):
            return cls.OWN_PERMISSION
        # check can write
        if checker.has_perm('edit_metadata_dataset_view', obj):
            return cls.MANAGE_PERMISSION
        return cls.READ_PERMISSION

    @classmethod
    def get_permissions_for_module(cls, obj, user):
        if user.is_superuser:
            return [cls.WRITE_PERMISSION.value]
        return []

    @classmethod
    def get_permissions_for_dataset(cls, obj, user):
        # check owner
        if user.has_perm('delete_dataset', obj):
            return [
                cls.OWN_PERMISSION.value,
                cls.MANAGE_PERMISSION.value,
                cls.WRITE_PERMISSION.value,
                cls.READ_PERMISSION.value,
            ]
        # check manager
        if (
            user.has_perm('dataset_add_view', obj)
        ):
            return [
                cls.MANAGE_PERMISSION.value,
                cls.WRITE_PERMISSION.value,
                cls.READ_PERMISSION.value,
            ]
        # check write only
        if (
            user.has_perm('upload_data', obj) or
            user.has_perm('review_upload', obj)
        ):
            return [
                cls.WRITE_PERMISSION.value,
                cls.READ_PERMISSION.value,
            ]
        return [cls.READ_PERMISSION.value]

    @classmethod
    def get_permissions_for_datasetview(cls, obj, user):
        # check owner
        if user.has_perm('edit_query_dataset_view', obj):
            return [
                cls.OWN_PERMISSION.value,
                cls.MANAGE_PERMISSION.value,
                cls.READ_PERMISSION.value,
            ]
        # check manager
        if (
            user.has_perm('edit_metadata_dataset_view', obj)
        ):
            return [
                cls.MANAGE_PERMISSION.value,
                cls.READ_PERMISSION.value,
            ]
        return [cls.READ_PERMISSION.value]


# Module Permission List
WRITE_MODULE_PERMISSION_LIST = [
    'module_add_dataset'
]

# Dataset Permission List
READ_DATASET_PERMISSION_LIST = [
    'view_dataset_level_1',
    'view_dataset_level_2',
    'view_dataset_level_3',
    'view_dataset_level_4'
]
WRITE_DATASET_PERMISSION_LIST = [
    'upload_data',
    'review_upload'
]
WRITE_DATASET_PERMISSION_LIST += READ_DATASET_PERMISSION_LIST
MANAGE_DATASET_PERMISSION_LIST = [
    'edit_metadata_dataset',
    'invite_user_dataset',
    'remove_user_dataset',
    'dataset_add_view'
]
MANAGE_DATASET_PERMISSION_LIST += WRITE_DATASET_PERMISSION_LIST
OWN_DATASET_PERMISSION_LIST = [
    'delete_dataset',
    'archive_dataset'
]
OWN_DATASET_PERMISSION_LIST += MANAGE_DATASET_PERMISSION_LIST

# View Permission List
READ_VIEW_PERMISSION_LIST = [
    'view_datasetview'
]
MANAGE_VIEW_PERMISSION_LIST = [
    'edit_metadata_dataset_view'
]
MANAGE_VIEW_PERMISSION_LIST += READ_VIEW_PERMISSION_LIST
OWN_VIEW_PERMISSION_LIST = [
    'edit_query_dataset_view',
    'delete_datasetview'
]
OWN_VIEW_PERMISSION_LIST += MANAGE_VIEW_PERMISSION_LIST

# external view permission list
EXTERNAL_READ_VIEW_PERMISSION_LIST = [
    'ext_view_datasetview_level_1',
    'ext_view_datasetview_level_2',
    'ext_view_datasetview_level_3',
    'ext_view_datasetview_level_4'
]


class GeoRepoBaseAccessPermission(BasePermission):
    message = 'You are not allowed to view this resource.'

    def has_permission(self, request, view):
        """Test if user is authenticated and active"""
        return request.user.is_authenticated and request.user.is_active


class ModuleAccessPermission(GeoRepoBaseAccessPermission):
    message = 'You are not allowed to view this module.'

    def has_object_permission(self, request, view, module):
        """Test if user has view permission to module"""
        return module.is_active


class DatasetDetailAccessPermission(GeoRepoBaseAccessPermission):
    message = 'You are not allowed to view this dataset.'

    def has_object_permission(self, request, view, dataset):
        """Test if user has view permission to dataset"""
        if not dataset.module.is_active:
            return False
        for i in range(MIN_PRIVACY_LEVEL, MAX_PRIVACY_LEVEL + 1):
            if request.user.has_perm(f'view_dataset_level_{i}', dataset):
                return True
        return False


class DatasetViewDetailAccessPermission(GeoRepoBaseAccessPermission):
    message = 'You are not allowed to view this dataset view.'

    def has_object_permission(self, request, view, dataset_view):
        """Test if user has view permission to dataset view"""
        if not dataset_view.dataset.module.is_active:
            return False
        has_read_perm = False
        max_privacy_level = 0
        for i in range(MAX_PRIVACY_LEVEL, MIN_PRIVACY_LEVEL - 1, -1):
            if (
                (request.user.has_perm('view_datasetview', dataset_view) and
                 request.user.has_perm(f'view_dataset_level_{i}',
                                       dataset_view.dataset)) or
                request.user.has_perm(f'ext_view_datasetview_level_{i}',
                                      dataset_view)
            ):
                has_read_perm = True
                max_privacy_level = i
                break
        if (
            has_read_perm and
            max_privacy_level < dataset_view.min_privacy_level
        ):
            has_read_perm = False
        return has_read_perm


def check_user_has_view_permission(user_or_obj, dataset_view,
                                   privacy_level=0):
    """Test whether user or external user or group can read a view."""
    if user_or_obj.has_perm('view_datasetview', dataset_view):
        return True
    if (
        privacy_level > 0 and
        user_or_obj.has_perm(
            f'ext_view_datasetview_level_{privacy_level}',
            dataset_view
        )
    ):
        return True
    # test for ext_view_datasetview_level_
    return (
        get_external_view_permission_privacy_level(user_or_obj,
                                                   dataset_view) > 0
    )


def get_view_permission_privacy_level(user_or_obj, dataset,
                                      dataset_view=None):
    """
    Get maximum privacy level that the user can access for dataset
    Return 0 if cannot access
    user_or_obj: user or ObjectPermissionChecker
    """
    dataset_privacy_level = 0
    view_privacy_level = 0
    for i in range(MAX_PRIVACY_LEVEL, MIN_PRIVACY_LEVEL - 1, -1):
        if user_or_obj.has_perm(f'view_dataset_level_{i}', dataset):
            dataset_privacy_level = i
            break
    if dataset_view:
        # search for permission of external user
        view_privacy_level = (
            get_external_view_permission_privacy_level(user_or_obj,
                                                       dataset_view)
        )
    return max(dataset_privacy_level, view_privacy_level)


def get_external_view_permission_privacy_level(user_or_obj, dataset_view):
    """
    Get maximum privacy level that external user can access for dataset_view
    Return 0 if cannot access
    user_or_obj: user or ObjectPermissionChecker
    """
    for i in range(MAX_PRIVACY_LEVEL, MIN_PRIVACY_LEVEL - 1, -1):
        if (
            user_or_obj.has_perm(f'ext_view_datasetview_level_{i}',
                                 dataset_view)
        ):
            return i
    return 0


def get_dataset_privacy_level_from_perms(permissions):
    """
    Get maximum privacy level that the user can access for dataset
    Return 0 if cannot access
    """
    for i in range(MAX_PRIVACY_LEVEL, MIN_PRIVACY_LEVEL - 1, -1):
        permission = f'view_dataset_level_{i}'
        if permission in permissions:
            return i
    return 0


def get_dataset_view_privacy_level_from_perms(permissions, dataset_perms):
    """
    Get maximum privacy level that the user can access for dataset_view
    Return 0 if cannot access
    """
    for i in range(MAX_PRIVACY_LEVEL, MIN_PRIVACY_LEVEL - 1, -1):
        ext_permission = f'ext_view_datasetview_level_{i}'
        if ext_permission in permissions:
            return i
        permission = f'view_dataset_level_{i}'
        if permission in dataset_perms:
            return i
    return 0


def get_views_for_user(user):
    datasets = Dataset.objects.all()
    datasets = get_dataset_for_user(user, datasets)
    views_querysets = DatasetView.objects.none()
    user_privacy_levels = {}
    for dataset in datasets:
        views = DatasetView.objects.filter(
            dataset=dataset
        )
        views, _ = get_dataset_views_for_user(
            user,
            dataset,
            views
        )
        views_querysets = views_querysets.union(views)
        privacy_level = get_view_permission_privacy_level(
            user,
            dataset
        )
        user_privacy_levels[dataset.id] = privacy_level
    # include external user
    external_views = DatasetView.objects.all()
    external_views = get_objects_for_user(
        user,
        EXTERNAL_READ_VIEW_PERMISSION_LIST,
        klass=external_views,
        use_groups=True,
        any_perm=True,
        accept_global_perms=False
    )
    views_querysets = views_querysets.union(external_views)
    views_querysets = views_querysets.order_by('created_at')
    return user_privacy_levels, views_querysets


def get_dataset_for_user(user, queryset, use_groups=True):
    """
    Return queryset for dataset with filter user can access
    """
    return get_objects_for_user(
        user,
        READ_DATASET_PERMISSION_LIST,
        klass=queryset,
        use_groups=use_groups,
        any_perm=True,
        accept_global_perms=False
    )


def get_dataset_views_for_user(user, dataset, queryset, use_groups=True):
    """
    Return views that the user can access by dataset, user_privacy_level
    """
    views = get_objects_for_user(
        user,
        'view_datasetview',
        klass=queryset,
        use_groups=use_groups,
        any_perm=True,
        accept_global_perms=False
    )
    # filter views based on privacy level
    user_privacy_level = get_view_permission_privacy_level(
        user, dataset
    )
    views = views.filter(
        min_privacy_level__lte=user_privacy_level
    )
    return views, user_privacy_level


def get_modules_to_add_dataset(user, queryset, use_groups=True):
    """
    Return queryset for module with filter user can add dataset
    """
    modules = get_objects_for_user(
        user,
        'module_add_dataset',
        klass=queryset,
        use_groups=use_groups,
        any_perm=True,
        accept_global_perms=False
    )
    return modules


def get_dataset_to_add_datasetview(user, queryset):
    """
    Return queryset for dataset with filter user can add view
    """
    datasets = get_objects_for_user(
        user,
        'dataset_add_view',
        klass=queryset,
        any_perm=True,
        accept_global_perms=False
    )
    return datasets


def get_dataset_to_review(user, queryset):
    """
    Return queryset for dataset with filter user can review
    """
    datasets = get_objects_for_user(
        user,
        'review_upload',
        klass=queryset,
        any_perm=True,
        accept_global_perms=False
    )
    return datasets


def check_user_or_group_superuser(user_or_group):
    """
    Test whether user_or_group is superuser
    Superuser does not need to be granted permissions
    """
    if user_or_group is None:
        return False
    if isinstance(user_or_group, User):
        return user_or_group.is_superuser
    return False


def grant_dataset_owner(dataset, user_or_group=None):
    """Called when dataset is created"""
    if user_or_group is None:
        user_or_group = dataset.created_by
    if check_user_or_group_superuser(user_or_group):
        return
    for permission in OWN_DATASET_PERMISSION_LIST:
        assign_perm(permission, user_or_group, dataset)
    # grant owner access to all views
    views = dataset.datasetview_set.all()
    for view in views:
        grant_datasetview_owner(view, user_or_group)


def reset_datasetview_cache(dataset_view, user_or_group):
    # clear permission cache for this dataset view resources+user
    for resource in dataset_view.datasetviewresource_set.all():
        if isinstance(user_or_group, Group):
            resource.clear_permission_cache()
        else:
            if Token.objects.filter(user=user_or_group).exists():
                resource.clear_permission_cache(
                    token=user_or_group.auth_token
                )


def grant_dataset_manager(dataset, user_or_group, permissions=None):
    """
    Called when dataset is shared to another user as manager
    permissions can contain OWN permission
    """
    if check_user_or_group_superuser(user_or_group):
        return
    # revoke all permissions first
    for permission in OWN_DATASET_PERMISSION_LIST:
        remove_perm(permission, user_or_group, dataset)
    if permissions is None:
        permissions = MANAGE_DATASET_PERMISSION_LIST
    for permission in permissions:
        assign_perm(permission, user_or_group, dataset)
    # grant manager access to all views
    views = dataset.datasetview_set.all()
    for view in views:
        grant_datasetview_manager(view, user_or_group)


def grant_dataset_viewer(dataset, user_or_group, privacy_level):
    """Called when dataset is shared to another user as viewer"""
    if check_user_or_group_superuser(user_or_group):
        return
    if privacy_level < MIN_PRIVACY_LEVEL or privacy_level > MAX_PRIVACY_LEVEL:
        raise ValueError(f'Invalid privacy level {privacy_level}')
    # revoke all permissions first
    for permission in OWN_DATASET_PERMISSION_LIST:
        remove_perm(permission, user_or_group, dataset)
    for i in range(MIN_PRIVACY_LEVEL, privacy_level + 1):
        permission = f'view_dataset_level_{i}'
        assign_perm(permission, user_or_group, dataset)
    # grant view access to all views
    views = dataset.datasetview_set.all()
    for view in views:
        grant_datasetview_viewer(view, user_or_group)


def grant_datasetview_owner(dataset_view, user_or_group=None):
    """Called when dataset view is created by dataset owner or manager"""
    if user_or_group is None:
        user_or_group = (
            dataset_view.created_by if dataset_view.created_by else
            dataset_view.dataset.created_by
        )
    if check_user_or_group_superuser(user_or_group):
        return
    for permission in OWN_VIEW_PERMISSION_LIST:
        assign_perm(permission, user_or_group, dataset_view)


def grant_datasetview_manager(dataset_view, user_or_group, permissions=None):
    """
    Called when:
    1. dataset is shared to another user as manager
    2. New view is created in dataset which manager has permission to
    permissions can also contain OWN
    """
    if check_user_or_group_superuser(user_or_group):
        return
    # revoke all permissions
    for permission in OWN_VIEW_PERMISSION_LIST:
        remove_perm(permission, user_or_group, dataset_view)
    if permissions is None:
        permissions = MANAGE_VIEW_PERMISSION_LIST
    for permission in permissions:
        assign_perm(permission, user_or_group, dataset_view)


def grant_datasetview_viewer(dataset_view, user_or_group):
    """
    Called when dataset is shared to another user as viewer
    Called when dataset_view is shared to another user as viewer

    UPDATE 2023-05-18:
    This function should only be used to grant permissions
    to viewer that inherits permission from dataset.
    If view is shared to another user that does not inheret from dataset,
    then should use:
    grant_datasetview_external_viewer(dataset_view, user, privacy_level)
    """
    if check_user_or_group_superuser(user_or_group):
        return
    # revoke all permissions
    for permission in OWN_VIEW_PERMISSION_LIST:
        remove_perm(permission, user_or_group, dataset_view)
    for permission in READ_VIEW_PERMISSION_LIST:
        assign_perm(permission, user_or_group, dataset_view)
    reset_datasetview_cache(dataset_view, user_or_group)


def grant_datasetview_external_viewer(dataset_view, user_or_group,
                                      privacy_level):
    """
    Called when dataset_view is shared to external user
    """
    if check_user_or_group_superuser(user_or_group):
        return
    if privacy_level < MIN_PRIVACY_LEVEL or privacy_level > MAX_PRIVACY_LEVEL:
        raise ValueError(f'Invalid privacy level {privacy_level}')
    # revoke all permissions first
    for permission in EXTERNAL_READ_VIEW_PERMISSION_LIST:
        remove_perm(permission, user_or_group, dataset_view)
    for i in range(MIN_PRIVACY_LEVEL, privacy_level + 1):
        permission = f'ext_view_datasetview_level_{i}'
        assign_perm(permission, user_or_group, dataset_view)
    reset_datasetview_cache(dataset_view, user_or_group)


def revoke_datasetview_access(dataset_view, user_or_group):
    """
    Called when dataset view is un-shared
    """
    permission_list = READ_VIEW_PERMISSION_LIST
    checker = ObjectPermissionChecker(user_or_group)
    if checker.has_perm('edit_query_dataset_view', dataset_view):
        # has own permission
        permission_list = OWN_VIEW_PERMISSION_LIST
    elif checker.has_perm('edit_metadata_dataset_view', dataset_view):
        # has manage permission
        permission_list = MANAGE_VIEW_PERMISSION_LIST
    for permission in permission_list:
        remove_perm(permission, user_or_group, dataset_view)
    reset_datasetview_cache(dataset_view, user_or_group)


def revoke_datasetview_external_viewer(dataset_view, user_or_group):
    """
    Called when dataset view is un-shared
    """
    permission_list = EXTERNAL_READ_VIEW_PERMISSION_LIST
    for permission in permission_list:
        remove_perm(permission, user_or_group, dataset_view)
    reset_datasetview_cache(dataset_view, user_or_group)


def revoke_dataset_access(dataset, user_or_group):
    """
    Called when dataset is un-shared
    """
    permission_list = READ_DATASET_PERMISSION_LIST
    checker = ObjectPermissionChecker(user_or_group)
    if checker.has_perm('delete_dataset', dataset):
        # has own permission
        permission_list = OWN_DATASET_PERMISSION_LIST
    elif checker.has_perm('dataset_add_view', dataset):
        # has manage permission
        permission_list = MANAGE_DATASET_PERMISSION_LIST
    elif checker.has_perm('upload_data', dataset):
        # has write permission
        permission_list = WRITE_DATASET_PERMISSION_LIST
    for permission in permission_list:
        remove_perm(permission, user_or_group, dataset)
    views = dataset.datasetview_set.all()
    for view in views:
        if checker.has_perm('view_datasetview', view):
            revoke_datasetview_access(view, user_or_group)


def grant_module_writer(module, user_or_group):
    """
    Called when Administrator invites user/group to module
    """
    if check_user_or_group_superuser(user_or_group):
        return
    for permission in WRITE_MODULE_PERMISSION_LIST:
        assign_perm(permission, user_or_group, module)


def revoke_module_writer(module, user_or_group):
    """
    Called when Administrator remove user/group from module
    """
    for permission in WRITE_MODULE_PERMISSION_LIST:
        remove_perm(permission, user_or_group, module)


def grant_dataset_to_public_groups(dataset):
    """
    Grant dataset as viewer level 1 to public groups
    E.g.: UNICEF group
    """
    groups = SitePreferences.preferences().default_public_groups
    for group_name in groups:
        group = Group.objects.filter(
            name=group_name
        ).first()
        if group:
            grant_dataset_viewer(dataset, group, 1)


def downgrade_creator_to_viewer(user: User):
    """
    Called when user role is changed from creator to viewer.

    This will revoke all write permissions from module/dataset/view.
    Then, it will apply read level 1 to previous datasets
    """
    modules = get_modules_to_add_dataset(
        user,
        Module.objects.all(),
        use_groups=False
    )
    for module in modules:
        revoke_module_writer(module, user)
    datasets = get_dataset_for_user(
        user,
        Dataset.objects.all(),
        use_groups=False
    )
    for dataset in datasets:
        revoke_dataset_access(dataset, user)
        grant_dataset_viewer(dataset, user, 1)


def check_user_type_for_view(user: User, view: DatasetView):
    """Check whether user is external or inherited type for view."""
    perms_queryset = DatasetView.objects.filter(
        id=view.id
    )
    perms_queryset = get_objects_for_user(
        user,
        'view_datasetview',
        perms_queryset,
        use_groups=False,
        any_perm=True,
        accept_global_perms=False
    )
    if perms_queryset.exists():
        return 'Inherited'
    return 'External'


def grant_dataset_to_application_keys(dataset: Dataset):
    """Grant dataset to registered application API keys.
    
    API keys for registered application will have following rules:
    - First Name = API_KEY
    - Last Name = {AppName}_lv_{privacyLevel}
    - Username = {AppName}_api_key_level_{privacyLevel}
    We can parse the privacy level from Username.
    
    :param dataset: Dataset object
    """
    # fetch Users with first_name = 'API_KEY'
    api_key_users = User.objects.filter(
        first_name='API_KEY',
        is_active=True
    )
    for api_key_user in api_key_users:
        # parse privacyLevel from username
        result = re.search(r'^(.+)_api_key_level_(\d+)$',
                           api_key_user.username)
        if not result:
            continue
        privacy_level = int(result.group(2))
        grant_dataset_viewer(dataset, api_key_user, privacy_level)
