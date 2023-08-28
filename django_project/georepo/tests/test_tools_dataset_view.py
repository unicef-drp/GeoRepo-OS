import mock
from django.test import TestCase
from georepo.models.dataset_view import (
    DatasetView,
    DATASET_VIEW_LATEST_TAG,
    DATASET_VIEW_ALL_VERSIONS_TAG,
    DATASET_VIEW_DATASET_TAG,
    DATASET_VIEW_SUBSET_TAG,
    DatasetViewResource
)
from georepo.tests.model_factories import (
    DatasetF, GeographicalEntityF
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    generate_default_view_dataset_all_versions,
    generate_default_view_adm0_latest,
    generate_default_view_adm0_all_versions,
    check_view_exists,
    trigger_generate_dynamic_views,
    get_view_resource_from_view
)


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_generate_vector_tiles(*args, **kwargs):
    return DummyTask('1')


def mocked_revoke_running_task(*args, **kwargs):
    return True


class TestToolsDatasetView(TestCase):

    def test_generate_default_view_dataset_latest(self):
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        generate_default_view_dataset_latest(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(default_type__isnull=True)
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World (Latest)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains only the latest entities '
            'from main dataset'
        )
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.IS_LATEST
        )
        self.assertIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_LATEST_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_LATEST_TAG,
            view.tags.values_list('name', flat=True)
        )

    def test_generate_default_view_dataset_all_versions(self):
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        generate_default_view_dataset_all_versions(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(default_type__isnull=True)
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World (All Versions)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains all the entities '
            'from main dataset'
        )
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.ALL_VERSIONS
        )
        self.assertNotIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_ALL_VERSIONS_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_DATASET_TAG,
            view.tags.values_list('name', flat=True)
        )

    @mock.patch(
        'dashboard.tasks.remove_view_resource_data.delay',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    def test_generate_default_view_adm0_latest(self):
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        adm0 = GeographicalEntityF.create(
            label='Pakistan',
            unique_code='PAK',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        # only 1 view is created
        generate_default_view_adm0_latest(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(
            default_type__isnull=True
        ).exclude(
            default_ancestor_code__isnull=True
        )
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World - Pakistan (Latest)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains only the latest entities '
            'from main dataset for Pakistan'
        )
        self.assertEqual(view.default_ancestor_code, adm0.unique_code)
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.IS_LATEST
        )
        self.assertIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_LATEST_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_SUBSET_TAG,
            view.tags.values_list('name', flat=True)
        )
        # remove adm0 and add another one
        old_uuid = str(view.uuid)
        adm0.delete()
        self.assertTrue(check_view_exists(old_uuid))
        adm0 = GeographicalEntityF.create(
            label='Syria',
            unique_code='SY',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        generate_default_view_adm0_latest(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(
            default_type__isnull=True
        ).exclude(
            default_ancestor_code__isnull=True
        )
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World - Syria (Latest)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains only the latest entities '
            'from main dataset for Syria'
        )
        self.assertEqual(view.default_ancestor_code, adm0.unique_code)
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.IS_LATEST
        )
        self.assertIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_LATEST_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_SUBSET_TAG,
            view.tags.values_list('name', flat=True)
        )

    @mock.patch(
        'dashboard.tasks.remove_view_resource_data.delay',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    def test_generate_default_view_adm0_all_versions(self):
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        adm0 = GeographicalEntityF.create(
            label='Pakistan',
            unique_code='PAK',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        # only 1 view is created
        generate_default_view_adm0_all_versions(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(
            default_type__isnull=True
        ).exclude(
            default_ancestor_code__isnull=True
        )
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World - Pakistan (All Versions)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains all the entities '
            'from main dataset for Pakistan'
        )
        self.assertEqual(view.default_ancestor_code, adm0.unique_code)
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.ALL_VERSIONS
        )
        self.assertNotIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_ALL_VERSIONS_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_SUBSET_TAG,
            view.tags.values_list('name', flat=True)
        )
        # remove adm0 and add another one
        old_uuid = str(view.uuid)
        adm0.delete()
        self.assertTrue(check_view_exists(old_uuid))
        adm0 = GeographicalEntityF.create(
            label='Syria',
            unique_code='SY',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        generate_default_view_adm0_all_versions(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(
            default_type__isnull=True
        ).exclude(
            default_ancestor_code__isnull=True
        )
        self.assertEqual(views.count(), 1)
        view = views.first()
        self.assertEqual(view.name, 'World - Syria (All Versions)')
        self.assertEqual(
            view.description,
            'Test. This dataset contains all the entities '
            'from main dataset for Syria'
        )
        self.assertEqual(view.default_ancestor_code, adm0.unique_code)
        self.assertEqual(
            view.default_type,
            DatasetView.DefaultViewType.ALL_VERSIONS
        )
        self.assertNotIn('is_latest=true', view.query_string)
        self.assertEqual(view.tags.count(), 2)
        self.assertIn(
            DATASET_VIEW_ALL_VERSIONS_TAG,
            view.tags.values_list('name', flat=True)
        )
        self.assertIn(
            DATASET_VIEW_SUBSET_TAG,
            view.tags.values_list('name', flat=True)
        )

    @mock.patch(
        'dashboard.tasks.generate_view_vector_tiles_task.apply_async'
    )
    @mock.patch('georepo.utils.dataset_view.app.control.revoke')
    def test_trigger_generate_dynamic_views(self, mocked_revoke, mocked_task):
        mocked_revoke.side_effect = mocked_revoke_running_task
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        adm0 = GeographicalEntityF.create(
            label='Pakistan',
            unique_code='PAK',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        generate_default_view_adm0_latest(dataset)
        views = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(
            default_type__isnull=True
        ).exclude(
            default_ancestor_code__isnull=True
        )
        self.assertEqual(views.count(), 1)
        # generate_view_vector_tiles_task should be called once
        mocked_task.side_effect = mocked_run_generate_vector_tiles
        trigger_generate_dynamic_views(dataset, export_data=False)
        mocked_task.assert_called()
        # create another adm0
        GeographicalEntityF.create(
            label='Syria',
            unique_code='SY',
            dataset=dataset,
            is_latest=True,
            is_approved=True
        )
        generate_default_view_adm0_latest(dataset)
        self.assertEqual(views.count(), 2)
        # generate_view_vector_tiles_task should be called twice
        mocked_task.reset_mock()
        mocked_task.side_effect = mocked_run_generate_vector_tiles
        trigger_generate_dynamic_views(dataset, export_data=False)
        mocked_task.assert_called()
        # generate_view_vector_tiles_task should be called once
        mocked_task.reset_mock()
        mocked_task.side_effect = mocked_run_generate_vector_tiles
        trigger_generate_dynamic_views(dataset, adm0, export_data=False)
        mocked_task.assert_called()


    def test_get_view_resource_from_view(self):
        dataset = DatasetF.create(
            label='World',
            description='Test'
        )
        generate_default_view_dataset_latest(dataset)
        view = DatasetView.objects.filter(
            dataset=dataset,
            is_static=False
        ).exclude(default_type__isnull=True).first()
        view.max_privacy_level = 1
        view.min_privacy_level = 1
        view.save()
        resource_1 = DatasetViewResource.objects.filter(
            dataset_view=view,
            privacy_level=1
        ).first()
        resource_1.entity_count = 10
        resource_1.save()
        # user with privacy level 1 and above can access resource_1
        result = get_view_resource_from_view(view, 1)
        self.assertTrue(result)
        self.assertEqual(result.resource_id, resource_1.resource_id)
        result = get_view_resource_from_view(view, 3)
        self.assertTrue(result)
        self.assertEqual(result.resource_id, resource_1.resource_id)
        view.max_privacy_level = 3
        view.min_privacy_level = 2
        view.save()
        resource_1.entity_count = 0
        resource_1.save()
        resource_2 = DatasetViewResource.objects.filter(
            dataset_view=view,
            privacy_level=2
        ).first()
        resource_2.entity_count = 10
        resource_2.save()
        # user with privacy level 2 and above can access resource_2
        with self.assertRaises(ValueError):
            result = get_view_resource_from_view(view, 1)
        result = get_view_resource_from_view(view, 4)
        self.assertTrue(result)
        self.assertEqual(result.resource_id, resource_2.resource_id)
