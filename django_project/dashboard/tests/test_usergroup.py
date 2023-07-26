from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.urls import reverse
from django.contrib.auth.models import Group
from georepo.tests.model_factories import (
    UserF, GroupF, DatasetF, DatasetViewF
)
from dashboard.api_views.groups import (
    GroupList,
    GroupDetail,
    GroupPermissionDetail,
    ManageUserGroup
)
from georepo.utils.permission import (
    grant_dataset_viewer
)


class TestGroupAPIViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(username='user_1')
        self.superuser = UserF.create(is_superuser=True)
        self.user_2 = UserF.create(username='user_2')
        self.group_1 = GroupF.create()
        self.user_1.groups.add(self.group_1)
        self.dataset_1 = DatasetF.create()

    def test_group_list(self):
        request = self.factory.get(
            reverse('group-list')
        )
        request.user = self.user_1
        view = GroupList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        request = self.factory.get(
            reverse('group-list')
        )
        request.user = self.superuser
        response = view(request)
        self.assertEqual(response.status_code, 200)
        # unicef group + group_1
        self.assertEqual(len(response.data), 2)

    def test_group_detail(self):
        kwargs = {
            'id': self.group_1.id
        }
        request = self.factory.get(
            reverse('group-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        view = GroupDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_members'], 1)
        # update group name
        kwargs = {
            'id': self.group_1.id
        }
        data = {
            'name': 'updated_group_name'
        }
        request = self.factory.post(
            reverse('group-detail', kwargs=kwargs),
            data=data,
            format='json'
        )
        request.user = self.superuser
        view = GroupDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 201)
        updated_group = Group.objects.get(id=self.group_1.id)
        self.assertEqual(updated_group.name, data['name'])
        # delete group
        tmp_group = GroupF.create()
        kwargs = {
            'id': tmp_group.id
        }
        request = self.factory.delete(
            reverse('group-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        view = GroupDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Group.objects.filter(id=tmp_group.id).exists())

    def test_user_group(self):
        tmp_group = GroupF.create()
        self.user_1.groups.add(tmp_group)
        # add new user to group
        kwargs = {
            'id': tmp_group.id,
            'user_id': self.user_2.id
        }
        request = self.factory.post(
            reverse('manage-user-group', kwargs=kwargs),
            data={}, format='json'
        )
        request.user = self.superuser
        view = ManageUserGroup.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        # list members
        kwargs = {
            'id': tmp_group.id
        }
        request = self.factory.get(
            reverse('manage-group-members', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ManageUserGroup.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        # delete member
        kwargs = {
            'id': tmp_group.id,
            'user_id': self.user_2.id
        }
        request = self.factory.delete(
            reverse('manage-user-group', kwargs=kwargs),
            data={}, format='json'
        )
        request.user = self.superuser
        view = ManageUserGroup.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)

    def test_group_permission_detail(self):
        # grant group_1 to dataset_1
        grant_dataset_viewer(self.dataset_1, self.group_1, 1)
        view = GroupPermissionDetail.as_view()
        kwargs = {
            'id': self.group_1.id,
            'object_type': 'dataset'
        }
        request = self.factory.get(
            reverse('group-permission-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        # module should return 0
        kwargs = {
            'id': self.group_1.id,
            'object_type': 'module'
        }
        request = self.factory.get(
            reverse('group-permission-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        # new view should inherit from dataset_1
        DatasetViewF.create(
            dataset=self.dataset_1
        )
        kwargs = {
            'id': self.group_1.id,
            'object_type': 'datasetview'
        }
        request = self.factory.get(
            reverse('group-permission-detail', kwargs=kwargs)
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
