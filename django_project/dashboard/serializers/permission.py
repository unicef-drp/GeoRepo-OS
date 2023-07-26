from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from guardian.core import ObjectPermissionChecker
from georepo.models import (
    Dataset,
    DatasetView
)
from georepo.utils.permission import (
    PermissionType,
    check_user_type_for_view,
    get_dataset_privacy_level_from_perms,
    get_dataset_view_privacy_level_from_perms
)

User = get_user_model()


class UserPermissionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    privacy_level = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()

    def get_name(self, obj: User):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username

    def get_role(self, obj: User):
        return obj.georeporole.type

    def get_permission(self, obj: User):
        checker = ObjectPermissionChecker(obj)
        permission = None
        object_type = self.context['object_type']
        perm_obj = self.context['perm_obj']
        if object_type == 'module':
            permission = (
                PermissionType.get_max_permission_for_module(perm_obj,
                                                             checker)
            )
        elif object_type == 'dataset':
            permission = (
                PermissionType.get_max_permission_for_dataset(perm_obj,
                                                              checker)
            )
        elif object_type == 'datasetview':
            permission = (
                PermissionType.get_max_permission_for_datasetview(
                    perm_obj, checker)
            )
        return permission.value if permission else ''

    def get_privacy_level(self, obj: User):
        checker = ObjectPermissionChecker(obj)
        # need to exclude permission from group
        user_perms = checker.get_user_perms(self.context['perm_obj'])
        object_type = self.context['object_type']
        if object_type == 'dataset':
            return get_dataset_privacy_level_from_perms(user_perms)
        elif object_type == 'datasetview':
            dataset = self.context['perm_obj'].dataset
            dataset_perms = checker.get_user_perms(dataset)
            return get_dataset_view_privacy_level_from_perms(
                user_perms,
                dataset_perms
            )
        return 0

    def get_type(self, obj: User):
        object_type = self.context['object_type']
        if object_type == 'datasetview':
            dataset_view = self.context['perm_obj']
            return check_user_type_for_view(obj, dataset_view)
        return None

    def get_editable(self, obj: User):
        object_type = self.context['object_type']
        requester = self.context['user']
        permission = self.get_permission(obj)
        editable = (
            permission in self.context['permissions'] and
            requester.id != obj.id
        )
        if object_type == 'datasetview':
            # for datasetview, inherited permissions are not editable
            dataset_view = self.context['perm_obj']
            if check_user_type_for_view(obj, dataset_view) != 'External':
                editable = False
        return editable

    def to_representation(self, instance: Group):
        representation = (
            super(UserPermissionSerializer, self).to_representation(instance)
        )
        privacy_level = representation['privacy_level']
        privacy_labels = self.context['privacy_labels']
        if privacy_level in privacy_labels:
            representation['privacy_label'] = privacy_labels[privacy_level]
        else:
            representation['privacy_label'] = ''
        return representation

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'role',
            'permission',
            'privacy_level',
            'type',
            'editable'
        ]


class GroupPermissionSerializer(serializers.ModelSerializer):
    permission = serializers.SerializerMethodField()
    privacy_level = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()

    def get_permission(self, obj: Group):
        checker = ObjectPermissionChecker(obj)
        permission = None
        object_type = self.context['object_type']
        perm_obj = self.context['perm_obj']
        if object_type == 'module':
            permission = (
                PermissionType.get_max_permission_for_module(perm_obj,
                                                             checker)
            )
        elif object_type == 'dataset':
            permission = (
                PermissionType.get_max_permission_for_dataset(perm_obj,
                                                              checker)
            )
        elif object_type == 'datasetview':
            permission = (
                PermissionType.get_max_permission_for_datasetview(
                    perm_obj, checker)
            )
        return permission.value if permission else ''

    def get_privacy_level(self, obj: Group):
        object_type = self.context['object_type']
        checker = ObjectPermissionChecker(obj)
        group_perms = checker.get_group_perms(self.context['perm_obj'])
        if object_type == 'dataset':
            return get_dataset_privacy_level_from_perms(group_perms)
        elif object_type == 'datasetview':
            dataset = self.context['perm_obj'].dataset
            dataset_perms = checker.get_group_perms(dataset)
            return get_dataset_view_privacy_level_from_perms(
                group_perms,
                dataset_perms
            )
        return 0

    def get_type(self, obj: Group):
        object_type = self.context['object_type']
        checker = ObjectPermissionChecker(obj)
        if object_type == 'datasetview':
            dataset_view = self.context['perm_obj']
            if checker.has_perm('view_datasetview', dataset_view):
                return 'Inherited'
            return 'External'
        return None

    def get_editable(self, obj: Group):
        object_type = self.context['object_type']
        checker = ObjectPermissionChecker(obj)
        permission = self.get_permission(obj)
        editable = (
            permission in self.context['permissions']
        )
        if object_type == 'datasetview':
            # for datasetview, inherited permissions are not editable
            dataset_view = self.context['perm_obj']
            if checker.has_perm('view_datasetview', dataset_view):
                editable = False
        return editable

    def to_representation(self, instance: Group):
        representation = (
            super(GroupPermissionSerializer, self).to_representation(instance)
        )
        privacy_level = representation['privacy_level']
        privacy_labels = self.context['privacy_labels']
        if privacy_level in privacy_labels:
            representation['privacy_label'] = privacy_labels[privacy_level]
        else:
            representation['privacy_label'] = ''
        return representation

    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'permission',
            'privacy_level',
            'type',
            'editable'
        ]


class UserActorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_name(self, obj: User):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username

    def get_role(self, obj: User):
        return obj.georeporole.type

    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'role'
        ]


class GroupActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id',
            'name'
        ]


class BaseObjectPermissionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    permission = serializers.SerializerMethodField()
    privacy_level = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    object_type = serializers.SerializerMethodField()
    privacy_label = serializers.SerializerMethodField()

    def to_representation(self, instance: Group):
        representation = (
            super(
                BaseObjectPermissionSerializer,
                self
            ).to_representation(instance)
        )
        privacy_level = representation['privacy_level']
        privacy_labels = self.context['privacy_labels']
        if privacy_level in privacy_labels:
            representation['privacy_label'] = privacy_labels[privacy_level]
        else:
            representation['privacy_label'] = ''
        return representation

    class Meta:
        fields = [
            'id',
            'name',
            'uuid',
            'permission',
            'privacy_level',
            'type',
            'object_type'
        ]


class DatasetPermissionSerializer(BaseObjectPermissionSerializer):

    def get_name(self, obj: Dataset):
        return obj.label

    def get_permission(self, obj: Dataset):
        checker = self.context['checker']
        return PermissionType.get_max_permission_for_dataset(
            obj, checker).value

    def get_privacy_level(self, obj: Dataset):
        checker = self.context['checker']
        is_group = self.context['is_group']
        if is_group:
            user_perms = checker.get_group_perms(obj)
        else:
            user_perms = checker.get_user_perms(obj)
        return get_dataset_privacy_level_from_perms(user_perms)

    def get_type(self, obj: Dataset):
        return ''

    def get_object_type(self, obj: Dataset):
        return 'dataset'

    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'uuid',
            'permission',
            'privacy_level',
            'type',
            'object_type'
        ]


class DatasetViewPermissionSerializer(BaseObjectPermissionSerializer):

    def get_name(self, obj: DatasetView):
        return obj.name

    def get_permission(self, obj: DatasetView):
        checker = self.context['checker']
        return PermissionType.get_max_permission_for_datasetview(
            obj, checker).value

    def get_privacy_level(self, obj: DatasetView):
        checker = self.context['checker']
        is_group = self.context['is_group']
        if is_group:
            user_perms = checker.get_group_perms(obj)
            dataset_perms = checker.get_group_perms(obj.dataset)
        else:
            user_perms = checker.get_user_perms(obj)
            dataset_perms = checker.get_user_perms(obj.dataset)
        return get_dataset_view_privacy_level_from_perms(
            user_perms,
            dataset_perms
        )

    def get_type(self, obj: DatasetView):
        checker = self.context['checker']
        return (
            'Inherited' if checker.has_perm('view_datasetview', obj) else
            'External'
        )

    def get_object_type(self, obj: DatasetView):
        return 'datasetview'

    class Meta:
        model = DatasetView
        fields = [
            'id',
            'name',
            'uuid',
            'permission',
            'privacy_level',
            'type',
            'object_type'
        ]
