import json
import datetime
from django.utils import timezone
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from georepo.utils import absolute_path
from georepo.models import (
    IdType,
    BackgroundTask,
    DatasetViewResource,
    DatasetView,
    Dataset
)
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF,
    EntityIdF,
    ModuleF,
    DatasetViewF
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest
)
from georepo.utils.dataset_view import (
    init_view_privacy_level
)
from georepo.tasks.celery_sync import (
    remove_old_background_tasks,
    check_celery_background_tasks,
    handle_task_failure
)


class TestCelerySync(TestCase):

    def setUp(self) -> None:
        self.pCode, _ = IdType.objects.get_or_create(name='PCode')
        self.gid, _ = IdType.objects.get_or_create(name='GID')
        self.entity_type = EntityTypeF.create(label='Country')
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(module=self.module)
        self.view_latest = generate_default_view_dataset_latest(
            self.dataset)[0]
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_1 = GeographicalEntityF.create(
                revision_number=1,
                level=0,
                dataset=self.dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                is_approved=True,
                is_latest=True,
                privacy_level=2
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.entity_1,
                default=True,
                value=self.entity_1.internal_code
            )
            EntityIdF.create(
                code=self.gid,
                geographical_entity=self.entity_1,
                default=False,
                value=self.entity_1.id
            )
        init_view_privacy_level(self.view_latest)

    def test_clear_old_background_task(self):
        task1 = BackgroundTask.objects.create(
            name='task1',
            last_update=timezone.now(),
            task_id='task1'
        )
        BackgroundTask.objects.create(
            name='task2',
            last_update=datetime.datetime(2000, 8, 14, 8, 8, 8),
            task_id='task2'
        )
        remove_old_background_tasks()
        tasks = BackgroundTask.objects.all()
        self.assertEqual(tasks.count(), 1)
        self.assertEqual(tasks.first().name, task1.name)

    def test_check_background_task(self):
        view = DatasetViewF.create()
        view_res = DatasetViewResource.objects.filter(
            dataset_view=view
        ).first()
        view_res.status = DatasetView.DatasetViewStatus.DONE
        view_res.vector_tile_sync_status = (
            DatasetViewResource.SyncStatus.SYNCED
        )
        view_res.save()
        view_res.refresh_from_db()
        self.assertEqual(
            view_res.vector_tile_sync_status,
            DatasetViewResource.SyncStatus.SYNCED
        )
        # create 1 failed task of generate vt
        BackgroundTask.objects.create(
            name='generate_view_resource_vector_tiles_task',
            last_update=timezone.now(),
            task_id='task1',
            parameters=f'({view_res.id},True,1)',
            status=BackgroundTask.BackgroundTaskStatus.STOPPED
        )
        # create 1 success task of generate vt
        BackgroundTask.objects.create(
            name='generate_view_resource_vector_tiles_task',
            last_update=timezone.now(),
            task_id='task2',
            parameters=f'({view_res.id},True,1)',
            status=BackgroundTask.BackgroundTaskStatus.COMPLETED
        )
        check_celery_background_tasks()
        # check if the generate vt status is successful
        view_res.refresh_from_db()
        self.assertEqual(
            view_res.vector_tile_sync_status,
            DatasetViewResource.SyncStatus.SYNCED
        )

    def test_handle_task_failure_vt(self):
        view = DatasetViewF.create()
        view_res = DatasetViewResource.objects.filter(
            dataset_view=view
        ).first()
        view_res.status = DatasetView.DatasetViewStatus.DONE
        view_res.vector_tile_sync_status = (
            DatasetViewResource.SyncStatus.SYNCED
        )
        view_res.save()
        task = BackgroundTask.objects.create(
            name='generate_view_resource_vector_tiles_task',
            last_update=timezone.now(),
            task_id='task1',
            parameters=f'({view_res.id},True,1)',
            status=BackgroundTask.BackgroundTaskStatus.STOPPED
        )
        handle_task_failure(task)
        view_res.refresh_from_db()
        self.assertEqual(
            view_res.vector_tile_sync_status,
            DatasetViewResource.SyncStatus.OUT_OF_SYNC
        )
        self.assertEqual(
            view_res.status,
            DatasetView.DatasetViewStatus.ERROR
        )

    def test_handle_task_failure_simplification(self):
        view = DatasetViewF.create()
        dataset = view.dataset
        task = BackgroundTask.objects.create(
            name='view_simplification_task',
            last_update=timezone.now(),
            task_id='task1',
            parameters=f'({view.id},)',
            status=BackgroundTask.BackgroundTaskStatus.STOPPED
        )
        handle_task_failure(task)
        view.refresh_from_db()
        dataset.refresh_from_db()
        self.assertEqual(
            view.simplification_sync_status,
            DatasetView.SyncStatus.OUT_OF_SYNC
        )
        self.assertEqual(
            dataset.simplification_sync_status,
            Dataset.SyncStatus.ERROR
        )
        self.assertEqual(
            dataset.simplification_progress,
            'Simplification error'
        )
        self.assertFalse(dataset.is_simplified)
