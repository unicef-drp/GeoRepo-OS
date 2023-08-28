import mock
import os
import json
from collections import OrderedDict
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from georepo.utils import absolute_path
from georepo.models import (
    DatasetTilingConfig,
    AdminLevelTilingConfig,
    IdType,
    DatasetView,
    DatasetViewResource
)
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF,
    EntityIdF,
    ModuleF
)
from georepo.utils.vector_tile import (
    create_view_configuration_files,
    generate_view_vector_tiles,
    dataset_view_sql_query
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest
)
from georepo.utils.dataset_view import (
    init_view_privacy_level
)


class DummyResult:
    def __init__(self):
        self.returncode = 0


def mock_subprocess_run(self, *args, **kwargs):
    return DummyResult()


def mock_shutil_move(src, dst):
    return 'OK'


def mock_generate_geojson(dataset):
    return True


def mock_os_path_exists(path):
    return False


def mocked_cache_get(self, *args, **kwargs):
    return OrderedDict()


@mock.patch('django.core.cache.cache.get',
            mock.Mock(side_effect=mocked_cache_get))
class TestVectorTile(TestCase):

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
        self.dataset_tconfig_1 = DatasetTilingConfig.objects.create(
            dataset=self.dataset,
            zoom_level=4
        )
        AdminLevelTilingConfig.objects.create(
            dataset_tiling_config=self.dataset_tconfig_1,
            level=self.entity_1.level
        )

    def test_dataset_view_sql_query(self):
        sql = dataset_view_sql_query(
            self.view_latest,
            0,
            4
        )
        self.assertIn(
            'ST_AsMVTGeom(GeomTransformMercator(gg.geometry), !BBOX!)', sql)
        self.assertIn(f'AND gg.dataset_id = {self.dataset.id}', sql)
        sql = dataset_view_sql_query(
            self.view_latest,
            0,
            4,
            0.5
        )
        self.assertIn(
            'SELECT ST_AsMVTGeom(GeomTransformMercator('
            'simplifygeometry(gg.geometry, 0.5)), !BBOX!)',
            sql
        )
        self.assertIn(f'AND gg.dataset_id = {self.dataset.id}', sql)

    def test_create_configuration_files(self):
        view_resource = DatasetViewResource.objects.get(
            dataset_view=self.view_latest,
            privacy_level=4
        )
        out_file_path = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'view-resource-{view_resource.id}-'
            f'{self.dataset_tconfig_1.zoom_level}.toml'
        )
        with mock.patch(
            'georepo.utils.vector_tile.open',
            mock.mock_open()
        ) as mocked_file:
            out_f_paths = create_view_configuration_files(view_resource)
            mocked_file.assert_called_once_with(out_file_path, 'w')
            self.assertEqual(len(out_f_paths), 1)
            self.assertEqual(out_file_path, out_f_paths[0]['config_file'])
            self.assertEqual(
                self.dataset_tconfig_1.zoom_level,
                out_f_paths[0]['zoom'])

    @mock.patch(
        'os.path.exists',
        mock.Mock(side_effect=mock_os_path_exists))
    @mock.patch(
        'shutil.move',
        mock.Mock(side_effect=mock_shutil_move))
    def test_generate_vector_tiles(self):
        # only privacy level 2 will be generated
        view_resource = DatasetViewResource.objects.get(
            dataset_view=self.view_latest,
            privacy_level=4
        )
        with mock.patch('subprocess.run') as mo_subprocess, \
            mock.patch(
                'georepo.utils.vector_tile.open',
                mock.mock_open()) as mocked_file:
            mo_subprocess.side_effect = mock_subprocess_run
            generate_view_vector_tiles(view_resource)
            mocked_file.assert_not_called()
            mo_subprocess.assert_not_called()
        view_resource = DatasetViewResource.objects.get(
            dataset_view=self.view_latest,
            privacy_level=3
        )
        with mock.patch('subprocess.run') as mo_subprocess, \
            mock.patch(
                'georepo.utils.vector_tile.open',
                mock.mock_open()) as mocked_file:
            mo_subprocess.side_effect = mock_subprocess_run
            generate_view_vector_tiles(view_resource)
            mocked_file.assert_not_called()
            mo_subprocess.assert_not_called()
        view_resource = DatasetViewResource.objects.get(
            dataset_view=self.view_latest,
            privacy_level=2
        )
        out_file_path = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'view-resource-{view_resource.id}-'
            f'{self.dataset_tconfig_1.zoom_level}.toml'
        )
        with mock.patch('subprocess.run') as mo_subprocess, \
            mock.patch(
                'georepo.utils.vector_tile.open',
                mock.mock_open()) as mocked_file:
            mo_subprocess.side_effect = mock_subprocess_run
            generate_view_vector_tiles(view_resource)
            mocked_file.assert_called_once_with(out_file_path, 'w')
            mo_subprocess.assert_called_once()
        updated_res = DatasetViewResource.objects.get(id=view_resource.id)
        self.assertEqual(updated_res.status,
                         DatasetView.DatasetViewStatus.DONE)
        self.assertEqual(updated_res.vector_tiles_progress, 100)
        view_resource = DatasetViewResource.objects.get(
            dataset_view=self.view_latest,
            privacy_level=1
        )
        with mock.patch('subprocess.run') as mo_subprocess, \
            mock.patch(
                'georepo.utils.vector_tile.open',
                mock.mock_open()) as mocked_file:
            mo_subprocess.side_effect = mock_subprocess_run
            generate_view_vector_tiles(view_resource)
            mocked_file.assert_not_called()
            mo_subprocess.assert_not_called()
