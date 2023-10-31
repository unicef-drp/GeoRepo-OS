import uuid
import json
import mock
from collections import OrderedDict
import io
import zipfile
from dateutil.parser import isoparse
from typing import List
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.test import APIRequestFactory
from rest_framework import versioning

from georepo.utils import absolute_path
from georepo.models import IdType, DatasetView, DatasetAdminLevelName
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, LanguageF, DatasetViewF,
    DatasetAdminLevelNameF, EntityIdF, IdTypeF, UserF, EntityNameF
)
from georepo.api_views.dataset_view import (
    DatasetViewList,
    DatasetViewListForUser,
    DatasetViewDetail,
    DatasetViewExportDownload,
    DatasetViewExportDownloadByLevel,
    DatasetViewExportDownloadByCountry,
    DatasetViewExportDownloadByCountryAndLevel
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    generate_default_view_adm0_latest,
    create_sql_view,
    check_view_exists,
    generate_view_bbox,
    calculate_entity_count_in_view
)
from georepo.utils.dataset_view import (
    init_view_privacy_level
)
from georepo.utils.permission import (
    grant_datasetview_external_viewer,
    grant_dataset_viewer
)


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_generate_vector_tiles(*args, **kwargs):
    return DummyTask('1')


def mocked_cache_get(self, *args, **kwargs):
    return OrderedDict()


class FakeResolverMatchV1:
    """Fake class to mock versioning"""
    namespace = 'v1'


class TestApiDatasetView(TestCase):

    def setUp(self) -> None:
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanist'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.entity_type = EntityTypeF.create(label='Country')
        self.factory = APIRequestFactory()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geometry = GEOSGeometry(geom_str)

    def setup_entities_for_dataset(self, dataset):
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            pak0_1 = GeographicalEntityF.create(
                dataset=dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=1,
                start_date=isoparse('2023-01-01T06:16:13Z'),
                end_date=isoparse('2023-01-10T06:16:13Z'),
                privacy_level=4
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=pak0_1,
                default=True,
                value=pak0_1.internal_code
            )
            EntityNameF.create(
                geographical_entity=pak0_1,
                name=pak0_1.label,
                language=self.enLang,
                idx=0
            )
        return pak0_1

    def check_disabled_module(self, dataset, view, request, kwargs=None):
        # disable module, should return 404
        dataset.module.is_active = False
        dataset.module.save()
        if kwargs:
            response = view(request, **kwargs)
        else:
            response = view(request)
        self.assertEqual(response.status_code, 404)

    @mock.patch(
        'dashboard.tasks.remove_view_resource_data.delay',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    def test_dataset_view_list(self):
        dataset = DatasetF.create()
        dataset_view = DatasetViewF.create(
            dataset=dataset
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse('v1:view-list-by-dataset', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = DatasetViewList.as_view(versioning_class=scheme)
        with self.assertNumQueries(9):
            response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(
            response.data['results'][0]['uuid'],
            str(dataset_view.uuid))
        self.assertEqual(
            len(response.data['results'][0]['bbox']),
            0
        )
        # generate sql view
        dataset_view.delete()
        views = generate_default_view_dataset_latest(dataset)
        # insert geom
        entity = self.setup_entities_for_dataset(dataset)
        dataset_view = views[0]
        init_view_privacy_level(dataset_view)
        calculate_entity_count_in_view(dataset_view)
        generate_view_bbox(dataset_view)
        with self.assertNumQueries(9):
            response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(
            response.data['results'][0]['uuid'],
            str(dataset_view.uuid))
        self.assertEqual(
            len(response.data['results'][0]['bbox']),
            4
        )
        # create a user with privacy level 3
        user_level_3 = UserF.create()
        grant_dataset_viewer(dataset, user_level_3, 3)
        # add entity with privacy level 2
        pak1 = GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            admin_level_name='Province',
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            geometry=entity.geometry,
            internal_code='PAK_1',
            revision_number=1,
            label='Pakistan_Province1',
            unique_code='PAK_1',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            privacy_level=2
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=pak1,
            default=True,
            value=pak1.internal_code
        )
        EntityNameF.create(
            geographical_entity=pak1,
            name=pak1.label,
            language=self.enLang,
            idx=0
        )
        # recalculate view metadata
        init_view_privacy_level(dataset_view)
        calculate_entity_count_in_view(dataset_view)
        generate_view_bbox(dataset_view)
        # ensure resource with level 4 and 2 are correct
        dataset_view.refresh_from_db()
        entity_count_map = {
            4: 1,
            3: 0,
            2: 1,
            1: 0
        }
        for privacy_level, assert_count in entity_count_map.items():
            resource = dataset_view.datasetviewresource_set.filter(
                privacy_level=privacy_level
            ).first()
            self.assertEqual(resource.entity_count, assert_count)
            if assert_count > 0:
                resource.vector_tiles_size = 1
                resource.save(update_fields=['vector_tiles_size'])
        # trigger view list API
        request = self.factory.get(
            reverse('v1:view-list-by-dataset', kwargs=kwargs)
        )
        request.user = user_level_3
        view = DatasetViewList.as_view(versioning_class=scheme)
        with self.assertNumQueries(13):
            response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(
            response.data['results'][0]['uuid'],
            str(dataset_view.uuid))
        resources = dataset_view.datasetviewresource_set.exclude(
            privacy_level=2
        )
        for resource in resources:
            self.assertNotIn(
                str(resource.uuid),
                response.data['results'][0]['vector_tiles'])
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=2
        ).first()
        self.assertIn(
            str(resource.uuid),
            response.data['results'][0]['vector_tiles'])
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)


    def test_dataset_view_list_for_user(self):
        dataset = DatasetF.create()
        views = generate_default_view_dataset_latest(dataset)
        # insert geom
        self.setup_entities_for_dataset(dataset)
        dataset_view = views[0]
        request = self.factory.get(
            reverse('v1:view-list')
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = DatasetViewListForUser.as_view(versioning_class=scheme)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), len(views))
        # new user, should return empty
        user_bob = UserF.create()
        request.user = user_bob
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)
        # invite new user to view as external user, should return 1
        grant_datasetview_external_viewer(dataset_view, user_bob, 3)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        # check disabled module, should return 0
        dataset.module.is_active = False
        dataset.module.save()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)

    def assert_view_detail(self, item, dataset_view: DatasetView,
                           adm_levels: List[DatasetAdminLevelName],
                           ext_ids: List[str]):
        statuses = dict(DatasetView.DatasetViewStatus.choices)
        self.assertEqual(
            item['status'],
            statuses[dataset_view.status]
        )
        self.assertNotIn('vector_tiles', item)
        self.assertEqual(item['name'], dataset_view.name)
        self.assertEqual(item['description'],
                         dataset_view.description)
        self.assertEqual(item['uuid'], str(dataset_view.uuid))
        self.assertEqual(item['last_update'],
                         dataset_view.last_update)
        self.assertIn('dataset_levels', item)
        self.assertEqual(len(item['dataset_levels']), len(adm_levels))
        for adm_level in adm_levels:
            dataset_level = [x for x in item['dataset_levels'] if
                             x['level'] == adm_level.level and
                             x['level_name'] == adm_level.label]
            self.assertTrue(dataset_level)
            dataset_level = dataset_level[0]
            self.assertIn('url', dataset_level)
            self.assertIn(str(dataset_view.uuid), dataset_level['url'])
            self.assertIn(f'level/{str(adm_level.level)}',
                          dataset_level['url'])
        self.assertIn('tags', item)
        self.assertEqual(len(item['tags']), dataset_view.tags.count())
        for tag in dataset_view.tags.all():
            self.assertIn(tag.name, item['tags'])
        self.assertIn('possible_id_types', item)
        self.assertEqual(len(item['possible_id_types']), len(ext_ids))
        for id in ext_ids:
            self.assertIn(id, item['possible_id_types'])

    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_dataset_view_detail(self):
        dataset = DatasetF.create()
        adm_levels = [
            DatasetAdminLevelNameF.create(
                dataset=dataset,
                label='Level_0',
                level=0
            )
        ]
        dataset_view = DatasetViewF.create(
            dataset=dataset,
            last_update=isoparse('2023-01-10T06:16:13Z'),
            is_static=False,
            query_string=(
                'SELECT * FROM georepo_geographicalentity where '
                f"dataset_id={dataset.id} AND revision_number=1"
            )
        )
        dataset_view.tags.add('abc')
        create_sql_view(dataset_view)
        self.assertTrue(check_view_exists(str(dataset_view.uuid)))
        kwargs = {
            'uuid': str(dataset_view.uuid)
        }
        request = self.factory.get(
            reverse(
                'v1:view-detail',
                kwargs=kwargs
            ) + '/?cached=false'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = DatasetViewDetail.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        id_types = [
            'ucode',
            'uuid',
            'concept_uuid'
        ]
        self.assert_view_detail(response.data, dataset_view,
                                adm_levels, id_types)
        self.assertEqual(len(response.data['bbox']), 0)
        # view for specific country, should use level names from entities
        geo_1 = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=self.entity_type,
            level=0,
            dataset=dataset,
            internal_code='PAK',
            label='Pakistan',
            is_approved=True,
            is_latest=True,
            unique_code='PAK',
            admin_level_name='TestLevel_0',
            revision_number=1,
            geometry=self.geometry
        )
        geo_2 = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=self.entity_type,
            level=1,
            dataset=dataset,
            internal_code='PAK_001',
            label='PAK_001',
            is_approved=True,
            is_latest=True,
            unique_code='PAK_001',
            admin_level_name='TestLevel_1',
            revision_number=1,
            parent=geo_1,
            ancestor=geo_1,
            geometry=self.geometry
        )
        geo_3 = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=self.entity_type,
            level=1,
            dataset=dataset,
            internal_code='PAK_002',
            label='PAK_002',
            is_approved=True,
            is_latest=True,
            unique_code='PAK_002',
            admin_level_name='TestLevel_1_dups',
            revision_number=1,
            parent=geo_1,
            ancestor=geo_1,
            geometry=self.geometry
        )
        new_id_type1 = IdTypeF.create(
            name='TESTCODE'
        )
        EntityIdF.create(
            code=new_id_type1,
            geographical_entity=geo_1
        )
        new_id_type2 = IdTypeF.create(
            name='TCODE'
        )
        EntityIdF.create(
            code=new_id_type2,
            geographical_entity=geo_2
        )
        dataset_view.default_type = DatasetView.DefaultViewType.IS_LATEST
        dataset_view.default_ancestor_code = geo_1.unique_code
        dataset_view.save(update_fields=['default_type',
                                         'default_ancestor_code'])
        generate_view_bbox(dataset_view)
        new_adm_levels = [
            DatasetAdminLevelName(
                dataset=dataset,
                label=geo_1.admin_level_name,
                level=0
            ),
            DatasetAdminLevelName(
                dataset=dataset,
                label=geo_2.admin_level_name,
                level=1
            ),
            DatasetAdminLevelName(
                dataset=dataset,
                label=geo_3.admin_level_name,
                level=1
            )
        ]
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        id_types = [
            'ucode',
            'uuid',
            'concept_uuid',
            'TESTCODE',
            'TCODE'
        ]
        self.assert_view_detail(response.data, dataset_view,
                                new_adm_levels, id_types)
        self.assertEqual(len(response.data['bbox']), 4)
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_dataset_view_export_download(self):
        dataset = DatasetF.create(
            label='ABC'
        )
        generate_default_view_dataset_latest(dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(dataset_view)
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=4
        ).first()
        resource.uuid = uuid.UUID('e59f8338-e8a8-4e6d-9e0d-c63108a8048e')
        resource.entity_count = 2
        resource.save()
        parent = GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK',
            unique_code_version=1
        )
        GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001',
            unique_code_version=1
        )
        kwargs = {
            'uuid': str(dataset_view.uuid)
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownload.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('ABC (Latest) adm0.geojson', name_list)
                self.assertIn('ABC (Latest) adm1.geojson', name_list)
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_dataset_view_export_download_by_level(self):
        dataset = DatasetF.create(
            label='ABC'
        )
        generate_default_view_dataset_latest(dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(dataset_view)
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=4
        ).first()
        resource.uuid = uuid.UUID('e59f8338-e8a8-4e6d-9e0d-c63108a8048e')
        resource.entity_count = 2
        resource.save()
        parent = GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK',
            unique_code_version=1
        )
        GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001',
            unique_code_version=1
        )
        kwargs = {
            'uuid': str(dataset_view.uuid),
            'admin_level': 1
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download-by-level',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownloadByLevel.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertNotIn('ABC (Latest) adm0.geojson', name_list)
                self.assertIn('ABC (Latest) adm1.geojson', name_list)
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_dataset_view_export_download_by_country(self):
        dataset = DatasetF.create(
            label='ABC'
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            label='Pakistan',
            unique_code='PAK',
            unique_code_version=1
        )
        GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001',
            unique_code_version=1
        )
        generate_default_view_adm0_latest(dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code='PAK'
        ).first()
        init_view_privacy_level(dataset_view)
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=4
        ).first()
        resource.uuid = uuid.UUID('e59f8338-e8a8-4e6d-9e0d-c63108a8048e')
        resource.entity_count = 2
        resource.save()
        kwargs = {
            'uuid': str(dataset_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_V1'
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download-by-country',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownloadByCountry.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('ABC - Pakistan (Latest) adm0.geojson',
                              name_list)
                self.assertIn('ABC - Pakistan (Latest) adm1.geojson',
                              name_list)
        # create latest view, should return the same for PAK_V1
        generate_default_view_dataset_latest(dataset)
        latest_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(latest_view)
        kwargs = {
            'uuid': str(latest_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_V1'
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download-by-country',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownloadByCountry.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('ABC - Pakistan (Latest) adm0.geojson',
                              name_list)
                self.assertIn('ABC - Pakistan (Latest) adm1.geojson',
                              name_list)
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_dataset_view_export_download_by_country_level(self):
        dataset = DatasetF.create(
            label='ABC'
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            label='Pakistan',
            unique_code='PAK',
            unique_code_version=1
        )
        GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001',
            unique_code_version=1
        )
        generate_default_view_adm0_latest(dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code='PAK'
        ).first()
        init_view_privacy_level(dataset_view)
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=4
        ).first()
        resource.entity_count = 2
        resource.uuid = uuid.UUID('e59f8338-e8a8-4e6d-9e0d-c63108a8048e')
        resource.save()
        kwargs = {
            'uuid': str(dataset_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_V1',
            'admin_level': 0
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download-by-country-and-level',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownloadByCountryAndLevel.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('ABC - Pakistan (Latest) adm0.geojson',
                              name_list)
                self.assertNotIn('ABC - Pakistan (Latest) adm1.geojson',
                                 name_list)
        # create latest view, should return the same for PAK_V1
        generate_default_view_dataset_latest(dataset)
        latest_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(latest_view)
        kwargs = {
            'uuid': str(latest_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_V1',
            'admin_level': 0
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-view-download-by-country-and-level',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetViewExportDownloadByCountryAndLevel.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('ABC - Pakistan (Latest) adm0.geojson',
                              name_list)
                self.assertNotIn('ABC - Pakistan (Latest) adm1.geojson',
                                 name_list)
        # check disabled module
        self.check_disabled_module(dataset, view, request, kwargs=kwargs)
