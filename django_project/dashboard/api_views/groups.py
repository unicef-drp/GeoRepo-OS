from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_group
from core.models import SitePreferences
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.utils.permission import (
    READ_DATASET_PERMISSION_LIST,
    EXTERNAL_READ_VIEW_PERMISSION_LIST
)
from dashboard.api_views.common import (
    IsSuperUser,
    get_privacy_level_labels
)
from dashboard.serializers.permission import (
    DatasetViewPermissionSerializer,
    DatasetPermissionSerializer
)


User = get_user_model()
OBJECT_TYPES = ['module', 'dataset', 'datasetview']


class GroupList(APIView):
    """List available groups."""
    permission_classes = [IsSuperUser]

    def get(self, request, *args, **kwargs):
        groups = Group.objects.all().order_by('id')
        response_data = []
        for group in groups:
            response_data.append({
                'id': group.id,
                'name': group.name
            })
        return Response(response_data)


class GroupDetail(APIView):
    """API to manage group."""
    permission_classes = [IsSuperUser]

    def get(self, request, *args, **kwargs):
        group = get_object_or_404(Group, id=kwargs.get('id'))
        return Response({
            'id': group.id,
            'name': group.name,
            'total_members': (
                User.objects.filter(
                    groups__id=group.id
                ).count()
            )
        })

    def post(self, request, *args, **kwargs):
        group_id = int(kwargs.get('id', '0'))
        if group_id > 0:
            group = get_object_or_404(Group, id=group_id)
            group.name = request.data.get('name')
            group.save()
        else:
            group = Group.objects.create(
                name=request.data.get('name')
            )
        return Response(status=201, data={
            'id': group.id
        })

    def delete(self, request, *args, **kwargs):
        group = get_object_or_404(Group, id=kwargs.get('id'))
        default_groups = SitePreferences.preferences().default_public_groups
        if group.name in default_groups:
            return Response(status=400, data={
                'detail': 'Unable to delete public group!'
            })
        group.delete()
        return Response(status=204)


class ManageUserGroup(APIView):
    """API to manage user in a group."""
    permission_classes = [IsSuperUser]

    def get(self, request, *args, **kwargs):
        """Return group members."""
        group = get_object_or_404(Group, id=kwargs.get('id'))
        users = User.objects.select_related(
            'georeporole'
        ).filter(
            groups__id=group.id
        ).order_by('id')
        response_data = []
        for user in users:
            if user.is_anonymous or user.username == 'AnonymousUser':
                continue
            role = (
                user.georeporole.type if
                user.georeporole and user.georeporole.type else '-'
            )
            if user.is_superuser:
                role = 'Admin'
            response_data.append({
                'id': user.id,
                'name': f'{user.first_name} {user.last_name}',
                'username': user.username,
                'email': user.email,
                'is_active': 'Yes' if user.is_active else 'No',
                'role': role,
                'joined_date': user.date_joined
            })
        return Response(response_data)

    def post(self, request, *args, **kwargs):
        """Add a user to group."""
        group = get_object_or_404(Group, id=kwargs.get('id'))
        user = get_object_or_404(User, id=kwargs.get('user_id'))
        user.groups.add(group)
        return Response(status=204)

    def delete(self, request, *args, **kwargs):
        """Remove a user from group."""
        group = get_object_or_404(Group, id=kwargs.get('id'))
        user = get_object_or_404(User, id=kwargs.get('user_id'))
        user.groups.remove(group)
        return Response(status=204)


class GroupPermissionDetail(APIView):
    """API to get group permission to an object."""
    permission_classes = [IsSuperUser]

    def get_modules(self, group):
        # no write permission is given to module
        return []

    def get_datasets(self, group, privacy_labels):
        checker = ObjectPermissionChecker(group)
        dataset = Dataset.objects.all()
        dataset = get_objects_for_group(
            group,
            READ_DATASET_PERMISSION_LIST,
            klass=dataset,
            any_perm=True,
            accept_global_perms=False
        )
        return DatasetPermissionSerializer(
            dataset,
            many=True,
            context={
                'checker': checker,
                'privacy_labels': privacy_labels,
                'is_group': True
            }
        ).data

    def get_dataset_views(self, group, privacy_labels):
        checker = ObjectPermissionChecker(group)
        views = DatasetView.objects.select_related('dataset').all()
        permission_list = ['view_datasetview']
        permission_list.extend(EXTERNAL_READ_VIEW_PERMISSION_LIST)
        views = get_objects_for_group(
            group,
            permission_list,
            klass=views,
            any_perm=True,
            accept_global_perms=False
        )
        return DatasetViewPermissionSerializer(
            views,
            many=True,
            context={
                'checker': checker,
                'privacy_labels': privacy_labels,
                'is_group': True
            }
        ).data

    def get(self, request, *args, **kwargs):
        group_id = kwargs.get('id')
        group = get_object_or_404(
            Group,
            id=group_id
        )
        object_type = kwargs.get('object_type')
        if object_type not in OBJECT_TYPES:
            raise ValidationError(f'Invalid object type: {object_type}')
        results = []
        privacy_labels = get_privacy_level_labels()
        if object_type == 'module':
            results = self.get_modules(group)
        elif object_type == 'dataset':
            results = self.get_datasets(group, privacy_labels)
        elif object_type == 'datasetview':
            results = self.get_dataset_views(group, privacy_labels)
        return Response(results)
