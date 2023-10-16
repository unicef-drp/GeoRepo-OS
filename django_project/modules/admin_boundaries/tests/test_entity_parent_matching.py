import json
from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase, override_settings

from core.settings.utils import absolute_path
from georepo.tests.model_factories import (
    GeographicalEntityF,
    DatasetF,
    LanguageF
)
from dashboard.models import (
    EntityUploadStatus, EntityUploadChildLv1,
    EntityTemp
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from dashboard.tools.validate_layer_file_0 import (
    preprocess_layer_file_0
)
from georepo.utils.layers import read_temp_layer_file
from modules.admin_boundaries.entity_parent_matching import (
    do_search_parent_entity_by_geometry,
    do_process_layer_files_for_parent_matching,
    do_process_layer_files_for_parent_matching_level0
)


class TestEntityParentMatching(TestCase):

    def setUp(self):
        self.dataset = DatasetF.create()
        self.geojson_0 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_0.geojson')
        with open(self.geojson_0) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_level0_1 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                unique_code='PAK',
                revision_number=1
            )
        self.geojson_1 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_1.geojson')
        with open(self.geojson_1) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geom_1 = GEOSGeometry(geom_str)
        self.geojson_0_2 = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        with open(self.geojson_0_2) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_level0_2 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='TEST1',
                unique_code='TEST1',
                revision_number=1
            )
        self.upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        language = LanguageF.create()
        self.layer_file = LayerFileF.create(
            layer_upload_session=self.upload_session,
            level=1,
            parent_id_field='adm0_id',
            entity_type='Country',
            name_fields=[
                {
                    'field': 'name_1',
                    'default': True,
                    'selectedLanguage': language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_1',
                    'default': True
                }
            ],
            layer_file=self.geojson_1
        )

    def test_do_search_parent_entity_by_geometry(self):
        test_geom_1 = self.entity_level0_1.geometry
        parent_entity, distance = do_search_parent_entity_by_geometry(
            test_geom_1,
            self.dataset
        )
        self.assertIsNotNone(parent_entity)
        self.assertEqual(parent_entity.id, self.entity_level0_1.id)
        self.assertAlmostEqual(distance, 100, 2)
        test_geom_2 = self.geom_1
        parent_entity, distance = do_search_parent_entity_by_geometry(
            test_geom_2,
            self.dataset
        )
        self.assertIsNotNone(parent_entity)
        self.assertEqual(parent_entity.id, self.entity_level0_1.id)
        # low overlaps area
        self.assertAlmostEqual(distance, 100, 2)

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_do_process_layer_files_for_parent_matching(self):
        do_process_layer_files_for_parent_matching(self.upload_session)
        uploads = EntityUploadStatus.objects.filter(
            upload_session=self.upload_session
        )
        self.assertEqual(uploads.count(), 1)
        upload = uploads.first()
        self.assertEqual(
            upload.original_geographical_entity.id,
            self.entity_level0_1.id)
        childs = EntityUploadChildLv1.objects.filter(
            entity_upload=upload
        )
        self.assertEqual(childs.count(), 1)
        self.assertEqual(childs.first().entity_id, 'PAK003')
        self.assertGreater(childs.first().overlap_percentage, 0)
        self.assertTrue(childs.first().is_parent_rematched)

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_do_process_layer_files_for_parent_matching_level0(self):
        dataset_2 = DatasetF.create()

        geojson_0 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_0.geojson')
        geojson_1 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_1.geojson')
        upload_session = LayerUploadSessionF.create(
            dataset=dataset_2
        )
        language = LanguageF.create()
        layer_file_0 = LayerFileF.create(
            layer_upload_session=upload_session,
            level=0,
            parent_id_field='',
            entity_type='Country',
            name_fields=[
                {
                    'field': 'name_0',
                    'default': True,
                    'selectedLanguage': language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_0',
                    'default': True
                }
            ],
            layer_file=geojson_0
        )
        LayerFileF.create(
            layer_upload_session=upload_session,
            level=1,
            parent_id_field='code_0',
            entity_type='Province',
            name_fields=[
                {
                    'field': 'name_1',
                    'default': True,
                    'selectedLanguage': language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_1',
                    'default': True
                }
            ],
            layer_file=geojson_1
        )
        # pre-process level0
        read_temp_layer_file(upload_session, layer_file_0)
        entity_uploads = preprocess_layer_file_0(
            upload_session
        )
        # do parent matching for level0
        do_process_layer_files_for_parent_matching_level0(upload_session,
                                                          entity_uploads)
        # check has EntityTemp
        self.assertTrue(EntityTemp.objects.filter(
            layer_file=layer_file_0
        ).exists())
        # check there are EntityUploadChildLv1 records
        self.assertEqual(len(entity_uploads), 1)
        upload = entity_uploads[0]
        children = EntityUploadChildLv1.objects.filter(
            entity_upload=upload
        )
        self.assertEqual(children.count(), 1)
        child = children.first()
        self.assertEqual(child.entity_id, 'PAK003')
        self.assertEqual(child.parent_entity_id, 'PAK')
        self.assertEqual(child.is_parent_rematched, False)
        self.assertEqual(child.feature_index, 0)
