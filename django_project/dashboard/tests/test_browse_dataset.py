from uuid import uuid4
import json
import datetime
from dateutil.parser import isoparse
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from django.contrib.gis.geos import GEOSGeometry
from georepo.utils import absolute_path
from dashboard.models import (
    EntitiesUserConfig
)
from georepo.tests.model_factories import (
    UserF,
    DatasetF,
    GeographicalEntityF,
    EntityTypeF,
    DatasetViewF
)
from dashboard.tests.model_factories import EntitiesUserConfigF
from dashboard.api_views.dataset import (
    DashboardDatasetFilter,
    DasboardDatasetEntityList,
    DatasetEntityDetail,
    DashboardDatasetFilterValue,
    DatasetMVTTiles,
    DatasetMVTTilesView,
    DatasetStyle,
    UpdateDatasetStyle
)
from georepo.models import (
    DatasetTilingConfig,
    AdminLevelTilingConfig,
    DatasetViewTilingConfig,
    ViewAdminLevelTilingConfig
)
from georepo.utils.permission import (
    grant_dataset_manager,
    grant_dataset_viewer
)


class TestDashboardDatasetFilter(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_get_dataset_filter(self):
        user_1 = UserF.create(username='test_1')
        dataset_1 = DatasetF.create()
        grant_dataset_viewer(dataset_1, user_1, 4)
        # first fetch, will create a new filter
        kwargs = {
            'id': dataset_1.id
        }
        request = self.factory.get(
            reverse('dashboard-dataset-filter', kwargs=kwargs)
        )
        request.user = user_1
        view = DashboardDatasetFilter.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filters'], {})
        self.assertTrue(EntitiesUserConfig.objects.filter(
            dataset=dataset_1,
            user=user_1
        ).exists())
        existing_config = EntitiesUserConfig.objects.filter(
            dataset=dataset_1,
            user=user_1
        ).first()
        # second fetch, will get existing filter
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter',
                kwargs=kwargs
            ) + f'?session={existing_config.uuid}'
        )
        request.user = user_1
        view = DashboardDatasetFilter.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filters'], {})
        self.assertEqual(EntitiesUserConfig.objects.filter(
            dataset=dataset_1,
            user=user_1
        ).count(), 1)
        # fetch using invalid uuid, will reuse old filter
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter',
                kwargs=kwargs
            ) + f'?session={uuid4()}'
        )
        request.user = user_1
        view = DashboardDatasetFilter.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filters'], {})
        self.assertEqual(EntitiesUserConfig.objects.filter(
            dataset=dataset_1,
            user=user_1
        ).count(), 1)


class TestDasboardDatasetEntityList(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_dataset_list(self):
        user_1 = UserF.create(username='test_1')
        dataset_1 = DatasetF.create()
        grant_dataset_viewer(dataset_1, user_1, 4)
        session_1 = EntitiesUserConfigF.create(
            user=user_1,
            dataset=dataset_1
        )
        kwargs = {
            'id': dataset_1.id,
            'session': session_1.uuid
        }
        filter_data_1 = {}
        request = self.factory.post(
            reverse('dashboard-dataset', kwargs=kwargs),
            filter_data_1
        )
        request.user = user_1
        view = DasboardDatasetEntityList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        filter_data_1 = {
            'country': ['Pakistan'],
            'type': ['District'],
            'level': [2],
            'level_name': ['ABC'],
            'revision': ['1'],
            'status': ['Approved'],
            'valid_from': datetime.datetime.now(),
            'search_text': 'abc'
        }
        request = self.factory.post(
            reverse('dashboard-dataset', kwargs=kwargs),
            filter_data_1
        )
        request.user = user_1
        view = DasboardDatasetEntityList.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)


class TestDatasetEntityDetail(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(username='test_1')
        self.dataset_1 = DatasetF.create()
        grant_dataset_manager(self.dataset_1, self.user_1)
        self.entity_type = EntityTypeF.create(label='Country')
        geojson_0_1_path = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset', 'level_0_1.geojson')
        with open(geojson_0_1_path) as geojson:
            data = json.load(geojson)
        geom_str = json.dumps(data['features'][0]['geometry'])
        self.geographical_entity = GeographicalEntityF.create(
            dataset=self.dataset_1,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            geometry=GEOSGeometry(geom_str),
            internal_code='PAK',
            revision_number=1
        )

    def test_entity_detail(self):
        kwargs = {
            'id': self.dataset_1.id,
            'entity_id': self.geographical_entity.id
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-detail',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DatasetEntityDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)


class TestDashboardDatasetFilterValue(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(username='test_1')
        self.dataset_1 = DatasetF.create()
        grant_dataset_manager(self.dataset_1, self.user_1)

    def test_get_filter_value(self):
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'status'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'country'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'level'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'level_name'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'type'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        kwargs = {
            'id': self.dataset_1.id,
            'criteria': 'revision'
        }
        request = self.factory.get(
            reverse(
                'dashboard-dataset-filter-values',
                kwargs=kwargs
            )
        )
        request.user = self.user_1
        view = DashboardDatasetFilterValue.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)


class TestDatasetMVTTiles(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.user_1 = UserF.create(username='test_1')
        self.superuser = UserF.create(is_superuser=True)
        self.dataset_1 = DatasetF.create()
        self.session_1 = EntitiesUserConfigF.create(
            user=self.user_1,
            dataset=self.dataset_1
        )
        self.entity_type = EntityTypeF.create(label='Country')
        geojson_0_1_path = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset', 'level_0_1.geojson')
        with open(geojson_0_1_path) as geojson:
            data = json.load(geojson)
        geom_str = json.dumps(data['features'][0]['geometry'])
        self.geographical_entity = GeographicalEntityF.create(
            dataset=self.dataset_1,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            geometry=GEOSGeometry(geom_str),
            internal_code='PAK',
            revision_number=1
        )
        tile_config = DatasetTilingConfig.objects.create(
            dataset=self.dataset_1,
            zoom_level=7
        )
        AdminLevelTilingConfig.objects.create(
            dataset_tiling_config=tile_config,
            level=self.geographical_entity.level,
            simplify_tolerance=0.009
        )
        self.geographical_entity.do_simplification()

    def test_get_tiles(self):
        kwargs = {
            'session': str(self.session_1.uuid),
            'z': 1,
            'x': 1,
            'y': 1
        }
        request = self.factory.get(
            reverse(
                'dashboard-tiles',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        view = DatasetMVTTiles.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        kwargs = {
            'session': str(self.session_1.uuid),
            'z': 7,
            'x': 89,
            'y': 51
        }
        request = self.factory.get(
            reverse(
                'dashboard-tiles',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        view = DatasetMVTTiles.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)

    def test_get_tiles_for_view(self):
        dataset_view = DatasetViewF.create(
            dataset=self.dataset_1,
            last_update=isoparse('2023-01-10T06:16:13Z'),
            is_static=False,
            query_string=(
                'SELECT * FROM georepo_geographicalentity where '
                f"dataset_id={self.dataset_1.id} AND revision_number=1"
            )
        )
        session = EntitiesUserConfigF.create(
            user=self.superuser,
            dataset=self.dataset_1,
            query_string=dataset_view.query_string
        )
        kwargs = {
            'dataset_view': str(dataset_view.uuid),
            'session': str(session.uuid),
            'z': 7,
            'x': 89,
            'y': 51
        }
        request = self.factory.get(
            reverse(
                'dashboard-tiles-view',
                kwargs=kwargs
            )
        )
        # will use config from dataset, exists
        request.user = self.superuser
        view = DatasetMVTTilesView.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # will use config from dataset, does not exist
        tiling_config = DatasetViewTilingConfig.objects.create(
            dataset_view=dataset_view,
            zoom_level=1
        )
        ViewAdminLevelTilingConfig.objects.create(
            view_tiling_config=tiling_config,
            level=0
        )
        kwargs = {
            'dataset_view': str(dataset_view.uuid),
            'session': str(session.uuid),
            'z': 7,
            'x': 89,
            'y': 51
        }
        request = self.factory.get(
            reverse(
                'dashboard-tiles-view',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        view = DatasetMVTTilesView.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)

    def test_dataset_style(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        kwargs = {
            'dataset': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse('get-dataset-style', kwargs=kwargs)
        )
        request.user = user
        view = DatasetStyle.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(dataset.uuid), response.data['sources'])
        # use custom style source name
        style_source_name = 'test_source_name'
        kwargs_update = {
            'uuid': str(dataset.uuid),
            'source_name': style_source_name
        }
        response.data['sources'][style_source_name] = (
            response.data['sources'][str(dataset.uuid)]
        )
        del response.data['sources'][str(dataset.uuid)]
        request = self.factory.post(
            reverse('update-dataset-style', kwargs=kwargs_update),
            response.data, format='json'
        )
        request.user = user
        view = UpdateDatasetStyle.as_view()
        response = view(request, **kwargs_update)
        self.assertEqual(response.status_code, 204)
        # refetch with custom style source name
        request = self.factory.get(
            reverse('get-dataset-style', kwargs=kwargs)
        )
        request.user = user
        view = DatasetStyle.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('test_source_name', response.data['sources'])
        # as download
        request = self.factory.get(
            reverse(
                'get-dataset-style',
                kwargs=kwargs
            ) + '/?download=True'
        )
        request.user = user
        view = DatasetStyle.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))
