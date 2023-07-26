import mock
import os
import json
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from georepo.utils import absolute_path
from georepo.models import (
    DatasetTilingConfig,
    AdminLevelTilingConfig,
    IdType
)
from georepo.tests.model_factories import (
    EntityTypeF,
    DatasetF,
    GeographicalEntityF,
    EntityIdF
)
from georepo.utils.vector_tile import (
    dataset_sql_query,
    create_configuration_file,
    create_configuration_files,
    generate_vector_tiles
)


def mock_subprocess_run(args):
    return 1


def mock_shutil_move(src, dst):
    return 'OK'


def mock_generate_geojson(dataset):
    return True


def mock_os_path_exists(path):
    return False


class TestVectorTile(TestCase):

    def setUp(self) -> None:
        self.pCode, _ = IdType.objects.get_or_create(name='PCode')
        self.gid, _ = IdType.objects.get_or_create(name='GID')
        self.entity_type = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
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
                is_latest=True
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
        self.dataset_tconfig_1 = DatasetTilingConfig.objects.create(
            dataset=self.dataset,
            zoom_level=4
        )
        AdminLevelTilingConfig.objects.create(
            dataset_tiling_config=self.dataset_tconfig_1,
            level=self.entity_1.level
        )

    def test_dataset_sql_query(self):
        sql = dataset_sql_query(
            self.dataset.id,
            0
        )
        self.assertIn('SELECT ST_AsBinary(gg.geometry)', sql)
        self.assertIn(f'AND gg.dataset_id = {self.dataset.id}', sql)
        sql = dataset_sql_query(
            self.dataset.id,
            1,
            0.5
        )
        self.assertIn(
            'SELECT ST_AsBinary(ST_SimplifyVW(gg.geometry',
            sql
        )
        self.assertIn(f'AND gg.dataset_id = {self.dataset.id}', sql)

    def test_create_configuration_files(self):
        out_file_path = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'dataset-{self.dataset.id}-'
            f'{self.dataset_tconfig_1.zoom_level}.toml'
        )
        with mock.patch(
            'georepo.utils.vector_tile.open',
            mock.mock_open()
        ) as mocked_file:
            out_f_paths = create_configuration_files(self.dataset)
            mocked_file.assert_called_once_with(out_file_path, 'w')
            self.assertEqual(len(out_f_paths), 1)
            self.assertEqual(out_file_path, out_f_paths[0]['config_file'])
            self.assertEqual(
                self.dataset_tconfig_1.zoom_level,
                out_f_paths[0]['zoom'])

    def test_create_configuration_file(self):
        out_file_path = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'dataset-{self.dataset.id}.toml'
        )
        with mock.patch(
            'georepo.utils.vector_tile.open',
            mock.mock_open()
        ) as mocked_file:
            out_f_path = create_configuration_file(self.dataset)
            mocked_file.assert_called_once_with(out_file_path, 'w')
            self.assertEqual(out_file_path, out_f_path)

    @mock.patch(
        'os.path.exists',
        mock.Mock(side_effect=mock_os_path_exists))
    @mock.patch(
        'shutil.move',
        mock.Mock(side_effect=mock_shutil_move))
    def test_generate_vector_tiles(self):
        out_file_path = os.path.join(
            '/',
            'opt',
            'tegola_config',
            f'dataset-{self.dataset.id}-'
            f'{self.dataset_tconfig_1.zoom_level}.toml'
        )
        with mock.patch('subprocess.run') as mo_subprocess, \
            mock.patch('georepo.utils.generate_geojson') \
            as mo_generate_geojson, \
            mock.patch('georepo.utils.generate_shapefile') \
            as mo_generate_shapefile, \
            mock.patch(
                'georepo.utils.vector_tile.open',
                mock.mock_open()) as mocked_file:
            mo_subprocess.side_effect = mock_subprocess_run
            mo_generate_geojson.side_effect = mock_generate_geojson
            mo_generate_shapefile.side_effect = mock_generate_geojson
            generate_vector_tiles(self.dataset)
            mocked_file.assert_called_once_with(out_file_path, 'w')
            mo_subprocess.assert_called_once()
            mo_generate_geojson.assert_called_once()
            mo_generate_shapefile.assert_called_once()
