from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseForbidden
from rest_framework.permissions import IsAdminUser
from georepo.utils.permission import (
    get_view_permission_privacy_level,
    READ_DATASET_PERMISSION_LIST,
    WRITE_DATASET_PERMISSION_LIST,
    MANAGE_DATASET_PERMISSION_LIST
)
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from dashboard.models.entity_upload import EntityUploadStatus
from dashboard.models.privacy_level import PrivacyLevel


class DatasetReadPermission(UserPassesTestMixin):

    def get_dataset_privacy_level(self, dataset, dataset_view=None):
        return get_view_permission_privacy_level(
            self.request.user,
            dataset,
            dataset_view=dataset_view
        )

    def can_add_upload(self, dataset):
        return self.request.user.has_perm(
            'upload_data',
            dataset
        )

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_id = self.kwargs.get('id', None)
        dataset_uuid = self.kwargs.get('uuid', None)
        dataset = None
        if dataset_id is not None and (
            (isinstance(dataset_id, str) and dataset_id.isnumeric()) or
            (isinstance(dataset_id, int))
        ):
            dataset = get_object_or_404(
                Dataset,
                id=dataset_id
            )
        elif dataset_id is not None:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_id
            )
        elif dataset_uuid is not None:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
        if dataset is None:
            raise Http404('Dataset is not found')
        view_uuid = self.request.GET.get('view_uuid', None)
        dataset_view = None
        if view_uuid:
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=view_uuid
            )
        privacy_level = self.get_dataset_privacy_level(dataset, dataset_view)
        return privacy_level > 0


class DatasetManagePermission(UserPassesTestMixin):

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_id = self.kwargs.get('id', None)
        dataset_uuid = self.kwargs.get('uuid', None)
        dataset = None
        if dataset_id is not None:
            dataset = get_object_or_404(
                Dataset,
                id=dataset_id
            )
        elif dataset_uuid is not None:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
        if dataset is None:
            raise Http404('Dataset is not found')
        permissions = list(
            set(MANAGE_DATASET_PERMISSION_LIST) -
            set(WRITE_DATASET_PERMISSION_LIST) -
            set(READ_DATASET_PERMISSION_LIST)
        )
        has_all_perms = True
        for permission in permissions:
            if not self.request.user.has_perm(permission, dataset):
                has_all_perms = False
                break
        return has_all_perms


class DatasetWritePermission(UserPassesTestMixin):

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_id = self.kwargs.get('id', None)
        dataset_uuid = self.kwargs.get('uuid', None)
        dataset = None
        if dataset_id is not None:
            dataset = get_object_or_404(
                Dataset,
                id=dataset_id
            )
        elif dataset_uuid is not None:
            dataset = get_object_or_404(
                Dataset,
                uuid=dataset_uuid
            )
        if dataset is None:
            raise Http404('Dataset is not found')
        permissions = list(
            set(WRITE_DATASET_PERMISSION_LIST) -
            set(READ_DATASET_PERMISSION_LIST)
        )
        has_all_perms = True
        for permission in permissions:
            if not self.request.user.has_perm(permission, dataset):
                has_all_perms = False
                break
        return has_all_perms


class EntityUploadStatusReadPermission(UserPassesTestMixin):

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        id = self.kwargs.get('id', None)
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=id
        )
        upload_session = entity_upload.upload_session
        dataset = upload_session.dataset
        permissions = list(
            set(WRITE_DATASET_PERMISSION_LIST) -
            set(READ_DATASET_PERMISSION_LIST)
        )
        has_all_perms = True
        for permission in permissions:
            if not self.request.user.has_perm(permission, dataset):
                has_all_perms = False
                break
        if not self.request.user.is_superuser:
            has_all_perms = (
                has_all_perms and
                self.request.user.id != upload_session.uploader.id
            )
        return has_all_perms


class IsSuperUser(IsAdminUser):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


def get_privacy_level_labels():
    privacy_levels = PrivacyLevel.objects.all()
    results = {}
    for level in privacy_levels:
        results[level.privacy_level] = level.label
    return results
