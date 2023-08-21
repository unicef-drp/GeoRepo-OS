from django.test import TestCase
from django.contrib.auth.models import Group
from guardian.core import ObjectPermissionChecker
from core.models.preferences import SitePreferences
from georepo.utils.permission import (
    check_user_type_for_view,
    get_view_permission_privacy_level,
    grant_datasetview_external_viewer,
    downgrade_creator_to_viewer,
    grant_module_writer,
    grant_dataset_owner,
    grant_dataset_manager,
    grant_dataset_viewer,
    grant_dataset_to_public_groups,
    revoke_module_writer,
    revoke_dataset_access,
    revoke_datasetview_external_viewer
)
from georepo.tests.model_factories import (
    UserF,
    DatasetF,
    DatasetViewF
)


class PermissionTestCase(TestCase):

    def setUp(self) -> None:
        self.user1 = UserF.create(
            is_active=True,
            username='user.test1@test.com'
        )
        self.user2 = UserF.create(
            is_active=True,
            username='user.test2@test.com'
        )
        self.user3 = UserF.create(
            is_active=True,
            username='user.test3@test.com'
        )
        self.api_key1 = UserF.create(
            is_active=True,
            first_name='API_KEY',
            last_name='TestApp_lv_1',
            username='TestApp_api_key_level_1',
        )
        self.api_key2 = UserF.create(
            is_active=True,
            first_name='API_KEY',
            last_name='TestApp2_lv_4',
            username='TestApp2_api_key_level_4',
        )
        self.api_key3 = UserF.create(
            is_active=False,
            first_name='API_KEY',
            last_name='TestApp3_lv_4',
            username='TestApp3_api_key_level_4',
        )

    def assert_dataset_view_privacy_level(self, dataset, obj, test_level,
                                          dataset_view = None):
        privacy_level = get_view_permission_privacy_level(
            obj, dataset, dataset_view=dataset_view
        )
        self.assertEqual(privacy_level, test_level)

    def assert_dataset_no_access(self, dataset, obj):
        self.assertFalse(self.user3.has_perm('delete_dataset', dataset))
        self.assertFalse(self.user3.has_perm('dataset_add_view', dataset))
        self.assertFalse(self.user3.has_perm('upload_data', dataset))
        self.assert_dataset_view_privacy_level(dataset, obj, 0)

    def test_grant_dataset_to_application_keys(self):
        dataset = DatasetF.create()
        self.assert_dataset_view_privacy_level(
            dataset, self.api_key1, 1)
        self.assert_dataset_view_privacy_level(
            dataset, self.api_key2, 4)
        self.assert_dataset_view_privacy_level(
            dataset, self.api_key3, 0)

    def test_check_user_type_for_view(self):
        dataset = DatasetF.create()
        dataset_view = DatasetViewF.create(
            dataset=dataset
        )
        grant_dataset_viewer(dataset, self.user1, 1)
        grant_datasetview_external_viewer(dataset_view, self.user2, 2)
        user_type = check_user_type_for_view(self.user1, dataset_view)
        self.assertEqual(user_type, 'Inherited')
        user_type = check_user_type_for_view(self.user2, dataset_view)
        self.assertEqual(user_type, 'External')

    def test_downgrade_creator_to_viewer(self):
        dataset = DatasetF.create()
        grant_dataset_owner(dataset, self.user1)
        grant_module_writer(dataset.module, self.user1)
        self.assertTrue(self.user1.has_perm('delete_dataset', dataset))
        self.assertTrue(self.user1.has_perm('module_add_dataset',
                                            dataset.module))
        downgrade_creator_to_viewer(self.user1)
        self.assertFalse(self.user1.has_perm('delete_dataset', dataset))
        self.assertFalse(self.user1.has_perm('module_add_dataset',
                                            dataset.module))
        self.assert_dataset_view_privacy_level(
            dataset, self.user1, 1)

    def test_grant_dataset_to_public_groups(self):
        dataset = DatasetF.create()
        groups = SitePreferences.preferences().default_public_groups
        for group_name in groups:
            group = Group.objects.filter(
                name=group_name
            ).first()
            if group is None:
                continue
            checker = ObjectPermissionChecker(group)
            self.assert_dataset_view_privacy_level(
                dataset, checker, 0)
        grant_dataset_to_public_groups(dataset)
        for group_name in groups:
            group = Group.objects.filter(
                name=group_name
            ).first()
            if group is None:
                continue
            checker = ObjectPermissionChecker(group)
            self.assert_dataset_view_privacy_level(
                dataset, checker, 1)

    def test_module_permission(self):
        dataset = DatasetF.create()
        grant_module_writer(dataset.module, self.user1)
        self.assertTrue(self.user1.has_perm('module_add_dataset',
                                            dataset.module))
        revoke_module_writer(dataset.module, self.user1)
        self.assertFalse(self.user1.has_perm('module_add_dataset',
                                            dataset.module))

    def test_dataset_permissions(self):
        dataset = DatasetF.create()
        # grant as owner dataset
        grant_dataset_owner(dataset, self.user1)
        self.assertTrue(self.user1.has_perm('delete_dataset', dataset))
        self.assert_dataset_view_privacy_level(
            dataset, self.user1, 4)
        # grant as manager dataset
        grant_dataset_manager(dataset, self.user2)
        self.assertFalse(self.user2.has_perm('delete_dataset', dataset))
        self.assertTrue(self.user2.has_perm('dataset_add_view', dataset))
        self.assertTrue(self.user2.has_perm('upload_data', dataset))
        self.assert_dataset_view_privacy_level(
            dataset, self.user2, 4)
        # grant as viewer dataset
        grant_dataset_viewer(dataset, self.user3, 1)
        self.assertFalse(self.user3.has_perm('delete_dataset', dataset))
        self.assertFalse(self.user3.has_perm('dataset_add_view', dataset))
        self.assertFalse(self.user3.has_perm('upload_data', dataset))
        self.assert_dataset_view_privacy_level(
            dataset, self.user3, 1)
        # revoke all access
        revoke_dataset_access(dataset, self.user1)
        revoke_dataset_access(dataset, self.user2)
        revoke_dataset_access(dataset, self.user3)
        self.assert_dataset_no_access(dataset, self.user1)
        self.assert_dataset_no_access(dataset, self.user2)
        self.assert_dataset_no_access(dataset, self.user3)

    def test_dataset_view_permissions(self):
        dataset = DatasetF.create()
        dataset_view = DatasetViewF.create(
            dataset=dataset
        )
        # inherit
        grant_dataset_viewer(dataset, self.user1, 1)
        # external user for view
        grant_datasetview_external_viewer(dataset_view, self.user2, 2)
        self.assert_dataset_view_privacy_level(dataset, self.user1,
                                               1, dataset_view)
        self.assert_dataset_view_privacy_level(dataset, self.user2,
                                               2, dataset_view)
        # revoke
        revoke_dataset_access(dataset, self.user1)
        self.assert_dataset_view_privacy_level(dataset, self.user1,
                                               0, dataset_view)
        revoke_datasetview_external_viewer(dataset_view, self.user2)
        self.assert_dataset_view_privacy_level(dataset, self.user2,
                                               0, dataset_view)
