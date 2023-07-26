import math
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from guardian.shortcuts import (
    get_users_with_perms,
    get_groups_with_perms,
    get_objects_for_user,
    get_objects_for_group
)
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.models import (
    Module,
    Dataset,
    DatasetView,
    GeorepoRole
)
from georepo.utils.permission import (
    PermissionType,
    grant_dataset_manager,
    grant_dataset_viewer,
    grant_dataset_owner,
    grant_module_writer,
    revoke_module_writer,
    revoke_dataset_access,
    revoke_datasetview_external_viewer,
    grant_datasetview_external_viewer,
    get_modules_to_add_dataset,
    get_dataset_to_add_datasetview,
    GeoRepoBaseAccessPermission,
    MANAGE_DATASET_PERMISSION_LIST,
    WRITE_DATASET_PERMISSION_LIST,
    READ_DATASET_PERMISSION_LIST,
    MANAGE_VIEW_PERMISSION_LIST,
    READ_VIEW_PERMISSION_LIST,
    get_dataset_for_user,
    EXTERNAL_READ_VIEW_PERMISSION_LIST
)
from dashboard.api_views.common import IsSuperUser
from dashboard.serializers.permission import (
    UserPermissionSerializer,
    GroupPermissionSerializer,
    UserActorSerializer,
    GroupActorSerializer
)
from dashboard.api_views.common import get_privacy_level_labels

User = get_user_model()


class ManageObjectAccessPermission(GeoRepoBaseAccessPermission):
    message = 'You are not allowed to manage this object.'

    def has_object_permission(self, request, view, object):
        """Test if user has Manage permission to object"""
        object_type = view.kwargs.get('object_type')
        result = True
        if request.user.is_superuser:
            result = True
        else:
            if object_type == 'module':
                result = request.user.is_superuser
            elif object_type == 'dataset':
                permissions = list(
                    set(MANAGE_DATASET_PERMISSION_LIST) -
                    set(WRITE_DATASET_PERMISSION_LIST) -
                    set(READ_DATASET_PERMISSION_LIST)
                )
                for permission in permissions:
                    if not request.user.has_perm(permission, object):
                        result = False
                        break
            elif object_type == 'datasetview':
                permissions = list(
                    set(MANAGE_VIEW_PERMISSION_LIST) -
                    set(READ_VIEW_PERMISSION_LIST)
                )
                for permission in permissions:
                    if not request.user.has_perm(permission, object):
                        result = False
                        break
            else:
                result = False
        return result


class PermissionActorList(AzureAuthRequiredMixin, APIView):
    """
    Return all actor (User/Group) that has permission to object
    """
    permission_classes = [ManageObjectAccessPermission]

    def get_obj(self, object_type, object_uuid):
        if object_type == 'module':
            obj = Module.objects.get(uuid=object_uuid)
        elif object_type == 'dataset':
            obj = Dataset.objects.get(uuid=object_uuid)
        elif object_type == 'datasetview':
            obj = DatasetView.objects.get(uuid=object_uuid)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return obj

    def get_permission_list_for_requester(self, object):
        permission_list = []
        if isinstance(object, Dataset):
            permission_list = PermissionType.get_permissions_for_dataset(
                object,
                self.request.user
            )
        elif isinstance(object, Module):
            permission_list = PermissionType.get_permissions_for_module(
                object,
                self.request.user
            )
        elif isinstance(object, DatasetView):
            permission_list = (
                PermissionType.get_permissions_for_datasetview(
                    object,
                    self.request.user
                )
            )
        return permission_list

    def validate_grant_permission(self, user_or_group, obj_permission, object):
        # reject if grant other than read permission to Viewer role
        if isinstance(user_or_group, User):
            # validate the user Role
            if user_or_group.georeporole.type is None:
                raise ValidationError(
                    'Invalid role assigned to user!')
            if (
                user_or_group.georeporole.type ==
                GeorepoRole.RoleType.VIEWER and
                obj_permission != PermissionType.READ_PERMISSION.value
            ):
                raise ValidationError(
                    f'Cannot assign permission {obj_permission} to viewer!')
        elif isinstance(user_or_group, Group):
            # validate only read permission
            if obj_permission != PermissionType.READ_PERMISSION.value:
                raise ValidationError(
                    f'Cannot assign permission {obj_permission} to Group!')
        # validate the obj_permission in allowed user to give permission
        permission_list = self.get_permission_list_for_requester(object)
        if obj_permission not in permission_list:
            raise ValidationError(
                f'You are not allowed to give {obj_permission}'
                'to other user!'
            )
        # for datasetview, only able to add Read to external user
        if (
            isinstance(object, DatasetView) and
            obj_permission != PermissionType.READ_PERMISSION.value
        ):
            raise ValidationError(
                f'You are not allowed to give {obj_permission}'
                'to external user!'
            )

    def grant_permission_dataset(self, dataset, user_or_group,
                                 obj_permission, obj_privacy_level):
        self.validate_grant_permission(user_or_group, obj_permission, dataset)
        if obj_permission == PermissionType.OWN_PERMISSION.value:
            grant_dataset_owner(dataset, user_or_group)
        elif obj_permission == PermissionType.MANAGE_PERMISSION.value:
            grant_dataset_manager(dataset, user_or_group)
        elif obj_permission == PermissionType.WRITE_PERMISSION.value:
            grant_dataset_manager(dataset, user_or_group,
                                  permissions=WRITE_DATASET_PERMISSION_LIST)
        elif obj_permission == PermissionType.READ_PERMISSION.value:
            if obj_privacy_level == 0:
                raise ValidationError(
                    f'Invalid privacy level assigned {obj_privacy_level}')
            grant_dataset_viewer(dataset, user_or_group, obj_privacy_level)

    def grant_permission_module(self, module, user_or_group,
                                obj_permission):
        self.validate_grant_permission(user_or_group, obj_permission, module)
        if obj_permission == PermissionType.WRITE_PERMISSION.value:
            grant_module_writer(module, user_or_group)

    def grant_permission_datasetview(self, datasetview, user_or_group,
                                     obj_permission, obj_privacy_level):
        self.validate_grant_permission(user_or_group, obj_permission,
                                       datasetview)
        if obj_permission == PermissionType.READ_PERMISSION.value:
            grant_datasetview_external_viewer(datasetview, user_or_group,
                                              obj_privacy_level)

    def revoke_permission_dataset(self, dataset, user_or_group):
        if isinstance(user_or_group, User):
            # TBC: check if other user revokes creator of the dataset
            if (
                self.request.user.id != dataset.created_by.id and
                user_or_group.id == dataset.created_by.id
            ):
                raise ValidationError('Cannot revoke dataset creator!')
        revoke_dataset_access(dataset, user_or_group)

    def revoke_permission_module(self, module, user_or_group):
        revoke_module_writer(module, user_or_group)

    def revoke_permission_datasetview(self, datasetview, user_or_group):
        revoke_datasetview_external_viewer(datasetview, user_or_group)

    def get_serializer(self):
        fetch_group = self.request.GET.get('is_group', False)
        if fetch_group:
            return GroupPermissionSerializer
        return UserPermissionSerializer

    def get(self, request, *args, **kwargs):
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.GET.get('page_size', '50'))
        search_text = self.request.GET.get('search_text', None)
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        # object uuid
        object_uuid = kwargs.get('uuid')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        object = self.get_obj(object_type, object_uuid)
        self.check_object_permissions(request, object)
        if fetch_group:
            actors = get_groups_with_perms(
                object
            )
            actors = actors.order_by('name')
            if search_text:
                actors = actors.filter(
                    name__icontains=search_text
                )
        else:
            actors = get_users_with_perms(
                object,
                with_group_users=False
            )
            actors = actors.order_by('first_name', 'last_name')
            if search_text:
                actors = actors.filter(
                    Q(username__icontains=search_text) |
                    Q(first_name__icontains=search_text) |
                    Q(last_name__icontains=search_text)
                )
        privacy_labels = get_privacy_level_labels()
        permission_list = self.get_permission_list_for_requester(object)
        paginator = Paginator(actors, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                self.get_serializer()(
                    paginated_entities,
                    many=True,
                    context={
                        'perm_obj': object,
                        'object_type': object_type,
                        'permissions': permission_list,
                        'user': self.request.user,
                        'privacy_labels': privacy_labels
                    }
                ).data
            )
        return Response(status=200, data={
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output,
            'permissions': permission_list
        })

    def post(self, request, *args, **kwargs):
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        # object uuid
        object_uuid = kwargs.get('uuid')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        object = self.get_obj(object_type, object_uuid)
        self.check_object_permissions(request, object)
        obj_user_or_group_id = request.data.get('id')
        obj_permission = request.data.get('permission')
        obj_privacy_level = request.data.get('privacy_level', 0)
        if fetch_group:
            user_or_group = Group.objects.get(id=obj_user_or_group_id)
        else:
            user_or_group = User.objects.select_related(
                'georeporole'
            ).get(id=obj_user_or_group_id)
        if object_type == 'dataset':
            self.grant_permission_dataset(object, user_or_group,
                                          obj_permission,
                                          obj_privacy_level)
        elif object_type == 'module':
            self.grant_permission_module(object, user_or_group,
                                         obj_permission)
        elif object_type == 'datasetview':
            self.grant_permission_datasetview(object, user_or_group,
                                              obj_permission,
                                              obj_privacy_level)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return Response(status=201)

    def delete(self, request, *args, **kwargs):
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        # object uuid
        object_uuid = kwargs.get('uuid')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        object = self.get_obj(object_type, object_uuid)
        self.check_object_permissions(request, object)
        # user_or_group id
        obj_user_or_group_id = kwargs.get('id')
        if fetch_group:
            user_or_group = Group.objects.get(id=obj_user_or_group_id)
        else:
            user_or_group = User.objects.select_related(
                'georeporole'
            ).get(id=obj_user_or_group_id)
        if object_type == 'dataset':
            self.revoke_permission_dataset(object, user_or_group)
        elif object_type == 'module':
            self.revoke_permission_module(object, user_or_group)
        elif object_type == 'datasetview':
            self.revoke_permission_datasetview(object, user_or_group)
        else:
            raise ValidationError(f'Invalid object type: {object_type}')
        return Response(status=200)


class GetPermissionUserAndRoles(PermissionActorList):
    permission_classes = [ManageObjectAccessPermission]

    def get(self, request, *args, **kwargs):
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        # object uuid
        object_uuid = kwargs.get('uuid')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        # fetch actor id
        actor_id = request.GET.get('id', None)
        object = self.get_obj(object_type, object_uuid)
        self.check_object_permissions(request, object)
        # filter by search text
        search_text = request.GET.get('search_text', None)
        if fetch_group:
            added_actors = get_groups_with_perms(
                object
            )
            groups = Group.objects.exclude(
                id__in=added_actors
            )
            if search_text:
                groups = groups.filter(
                    name__icontains=search_text
                )
            elif actor_id:
                groups = Group.objects.filter(
                    id=actor_id
                )
            else:
                groups = groups.order_by('name')[:20]
            actors = GroupActorSerializer(
                groups,
                many=True
            )
        else:
            added_actors = get_users_with_perms(
                object,
                with_group_users=False
            )
            users = User.objects.exclude(
                id__in=added_actors
            ).exclude(
                georeporole__type__isnull=True
            ).exclude(
                is_superuser=True
            ).exclude(
                is_active=False
            ).select_related('georeporole')
            if object_type == 'module':
                users = users.exclude(
                    georeporole__type=GeorepoRole.RoleType.VIEWER
                )
            if search_text:
                users = users.filter(
                    Q(first_name__icontains=search_text) |
                    Q(last_name__icontains=search_text) |
                    Q(username__icontains=search_text) |
                    Q(email__icontains=search_text)
                )
            elif actor_id:
                users = User.objects.filter(
                    id=actor_id
                )
            else:
                users = users.order_by('username')[:20]
            actors = UserActorSerializer(
                users,
                many=True
            )
        return Response(
            status=200,
            data={
                'actors': actors.data
            }
        )


class GetAvailablePermissionForObject(PermissionActorList):
    permission_classes = [ManageObjectAccessPermission]

    def get_group_permissions(self):
        # only return read permission for group
        return [PermissionType.READ_PERMISSION.value]

    def get(self, request, *args, **kwargs):
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        # object uuid
        object_uuid = kwargs.get('uuid')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        object = self.get_obj(object_type, object_uuid)
        self.check_object_permissions(request, object)
        if fetch_group:
            permissions = self.get_group_permissions()
        else:
            permissions = (
                self.get_permission_list_for_requester(object)
            )
            if object_type == 'datasetview':
                # permission available for this is to invite external user
                # with read permission
                permissions = [PermissionType.READ_PERMISSION.value]
        return Response(
            status=200,
            data={
                'permissions': permissions
            }
        )


class CanCreateDataset(AzureAuthRequiredMixin, APIView):
    """
    Check whether user has access to create dataset in any module
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        modules = Module.objects.all()
        modules = get_modules_to_add_dataset(
            request.user,
            modules
        )
        datasets = Dataset.objects.all()
        datasets = get_dataset_to_add_datasetview(
            request.user,
            datasets
        )
        return Response(
            status=200,
            data={
                'can_create_dataset': modules.exists(),
                'can_create_datasetview': datasets.exists()
            }
        )


class GetAvailableObjectForActor(APIView):
    """Search object that available to be assigned permission to actor."""
    permission_classes = [IsSuperUser]

    def get_single_object(self, object_type, selected_uuid):
        result = {
            'object_type': object_type,
            'name': '',
            'uuid': ''
        }
        if object_type == 'module':
            module = Module.objects.filter(
                uuid=selected_uuid
            ).first()
            if module:
                result = {
                    'object_type': object_type,
                    'name': module.name,
                    'uuid': str(module.uuid)
                }
        elif object_type == 'dataset':
            dataset = Dataset.objects.filter(
                uuid=selected_uuid
            ).first()
            if dataset:
                result = {
                    'object_type': object_type,
                    'name': dataset.label,
                    'uuid': str(dataset.uuid)
                }
        elif object_type == 'datasetview':
            view = DatasetView.objects.filter(
                uuid=selected_uuid
            ).first()
            if view:
                result = {
                    'object_type': object_type,
                    'name': view.name,
                    'uuid': str(view.uuid)
                }
        return result

    def search_module(self, user_or_group, search_text):
        if isinstance(user_or_group, Group):
            return []
        existing_modules = get_modules_to_add_dataset(
            user_or_group,
            Module,
            use_groups=False
        )
        available_modules = Module.objects.exclude(
            id__in=existing_modules
        )
        if search_text:
            available_modules = available_modules.filter(
                name__icontains=search_text
            )
        return [{
            'object_type': 'module',
            'name': module.name,
            'uuid': str(module.uuid)
        } for module in available_modules]

    def search_dataset(self, user_or_group, search_text):
        if isinstance(user_or_group, Group):
            existing_datasets = get_objects_for_group(
                user_or_group,
                READ_DATASET_PERMISSION_LIST,
                klass=Dataset,
                any_perm=True,
                accept_global_perms=False
            )
        else:
            existing_datasets = get_dataset_for_user(
                user_or_group,
                Dataset,
                use_groups=False
            )
        available_datasets = Dataset.objects.filter(
            is_active=True
        ).exclude(
            id__in=existing_datasets
        )
        if search_text:
            available_datasets = available_datasets.filter(
                label__icontains=search_text
            )
        else:
            available_datasets = available_datasets[:30]
        return [{
            'object_type': 'dataset',
            'name': dataset.label,
            'uuid': str(dataset.uuid)
        } for dataset in available_datasets]

    def search_dataset_view(self, user_or_group, search_text):
        permission_list = ['view_datasetview']
        permission_list.extend(EXTERNAL_READ_VIEW_PERMISSION_LIST)
        if isinstance(user_or_group, Group):
            existing_views = get_objects_for_group(
                user_or_group,
                permission_list,
                klass=DatasetView,
                any_perm=True,
                accept_global_perms=False
            )
        else:
            existing_views = get_objects_for_user(
                user_or_group,
                permission_list,
                klass=DatasetView,
                use_groups=False,
                any_perm=True,
                accept_global_perms=False
            )
        available_views = DatasetView.objects.filter(
            dataset__is_active=True
        ).exclude(
            id__in=existing_views
        )
        if search_text:
            available_views = available_views.filter(
                name__icontains=search_text
            )
        else:
            available_views = available_views[:30]
        return [{
            'object_type': 'datasetview',
            'name': view.name,
            'uuid': str(view.uuid)
        } for view in available_views]

    def get(self, request, *args, **kwargs):
        # MODULE, DATASET, DATASETVIEW
        object_type = kwargs.get('object_type')
        actor_id = kwargs.get('actor_id')
        # fetch group
        fetch_group = request.GET.get('is_group', False)
        if fetch_group:
            user_or_group = get_object_or_404(Group, id=actor_id)
        else:
            user_or_group = get_object_or_404(User, id=actor_id)
        # filter by search text
        search_text = request.GET.get('search_text', None)
        # filter by selected uuid
        selected_uuid = request.GET.get('uuid', None)
        results = []
        if selected_uuid:
            results.append(self.get_single_object(object_type, selected_uuid))
        else:
            if object_type == 'module':
                results = self.search_module(user_or_group, search_text)
            elif object_type == 'dataset':
                results = self.search_dataset(user_or_group, search_text)
            elif object_type == 'datasetview':
                results = self.search_dataset_view(user_or_group, search_text)
        return Response(
            status=200,
            data={
                'objects': results
            }
        )


class FetchPrivacyLevelLabels(APIView):
    """Fetch available privacy level labels."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(status=200, data=get_privacy_level_labels())
