import json

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase

from core.settings.utils import absolute_path
from dashboard.models.boundary_comparison import BoundaryComparison
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF, \
    EntityUploadF
from georepo.models import GeographicalEntity
from georepo.tests.model_factories import (
    GeographicalEntityF,
    DatasetF,
    EntityNameF
)
from modules.admin_boundaries.admin_boundary_matching import (
    AdminBoundaryMatching
)


class TestBoundaryMatching(TestCase):

    def setUp(self):
        self.dataset = DatasetF.create()
        self.entity_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        self.entity_2_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entity_2.geojson')
        self.entity_3_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entity_3.geojson')
        self.entity_4_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entity_4.geojson')
        entity_geojson = [
            self.entity_1_geojson,
            self.entity_2_geojson,
            self.entity_3_geojson,
            self.entity_4_geojson
        ]
        index = 0
        self.geographical_entities = []
        for entity_geojson_path in entity_geojson:
            with open(entity_geojson_path) as geojson:
                data = json.load(geojson)
                geom_str = json.dumps(data['features'][0]['geometry'])
                self.geographical_entities.append(GeographicalEntityF.create(
                    dataset=self.dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=f'CODE_{index}',
                    unique_code=f'CODE_{index}',
                    revision_number=1
                ))
            index += 1

    def test_find_highest_overlap(self):
        source_entity = self.geographical_entities[0]
        target_entities = GeographicalEntity.objects.filter(
            id__in=[
                self.geographical_entities[1].id,
                self.geographical_entities[2].id,
                self.geographical_entities[3].id,
            ]
        )
        highest_overlap, overlap_new, overlap_old = (
            AdminBoundaryMatching.highest_overlap(
                entity_source=source_entity,
                entity_target=target_entities
            )
        )
        self.assertEqual(
            highest_overlap,
            self.geographical_entities[1]
        )

    def test_name_similarity(self):
        source_entity = self.geographical_entities[0]
        target_entity = self.geographical_entities[1]
        name_similarity = AdminBoundaryMatching.name_similarity(
            source_entity,
            target_entity
        )
        self.assertGreaterEqual(
            name_similarity,
            0.8
        )

        EntityNameF.create(
            name='East Azarbaijan',
            geographical_entity=source_entity,
            default=True
        )
        EntityNameF.create(
            name='Azarbayejan-e Sharghi',
            geographical_entity=target_entity,
            default=True
        )
        name_similarity = AdminBoundaryMatching.name_similarity(
            source_entity,
            target_entity
        )
        self.assertEqual(
            name_similarity,
            0.5
        )

    def test_check_code(self):
        code_match = AdminBoundaryMatching.check_code(
            self.geographical_entities[0],
            self.geographical_entities[1],
        )
        self.assertFalse(code_match)

        geo_1 = GeographicalEntityF.create(unique_code='ISO1')
        geo_2 = GeographicalEntityF.create(unique_code='ISO1')

        code_match = AdminBoundaryMatching.check_code(
            geo_1,
            geo_2,
        )
        self.assertTrue(code_match)

    def test_run_admin_boundary_matching(self):
        upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session
        )
        geo_1 = GeographicalEntityF.create(
            dataset=self.dataset,
            revision_number=1
        )
        geo_2 = GeographicalEntityF.create(
            dataset=self.dataset,
            revision_number=2,
            layer_file=layer_file
        )
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_1,
            revised_geographical_entity=geo_2
        )

        # Test admin_boundary_matching without geometries
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        self.assertFalse(BoundaryComparison.objects.filter(
            main_boundary=geo_1
        ).exists())

        # Test admin_boundary_matching without previous entities
        dataset = DatasetF.create()
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file = LayerFileF.create(layer_upload_session=upload_session)
        geo_2 = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=2,
            layer_file=layer_file
        )
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        self.assertFalse(BoundaryComparison.objects.filter(
            main_boundary=geo_2
        ).exists())

    def setup_boundary_matching(self, dataset,
                                geojson_file='entities_1.geojson'):
        entity_parent_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'parent.geojson')
        with open(entity_parent_geojson) as geojson:
            data = json.load(geojson)
            feature = data['features'][0]
            geom_str = json.dumps(feature['geometry'])
            geo_parent = GeographicalEntityF.create(
                dataset=dataset,
                revision_number=1,
                level=0,
                internal_code='CODE',
                unique_code='CODE',
                unique_code_version=1,
                geometry=GEOSGeometry(geom_str),
                is_latest=True,
                is_approved=True
            )
        entities_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            geojson_file)
        index = 0
        geographical_entities = []
        with open(entities_1_geojson) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                internal_code = str(feature['properties']['id'])
                sequence_number = str(index + 1).zfill(4)
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=internal_code,
                    unique_code=f'CODE_{sequence_number}',
                    revision_number=1,
                    unique_code_version=1,
                    level=1,
                    parent=geo_parent,
                    ancestor=geo_parent
                ))
                index += 1
        return geo_parent, geographical_entities

    def test_run_boundary_matching_ucode_normal_with_reuse(self):
        dataset = DatasetF.create()
        geo_parent_v1, _ = self.setup_boundary_matching(
            dataset
        )
        geo_parent = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=1,
            level=0,
            unique_code='CODE',
            unique_code_version=1
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file = LayerFileF.create(layer_upload_session=upload_session)
        # load from entities_2 with reordered features
        entities_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entities_2.geojson')
        index = 0
        geographical_entities = []
        with open(entities_1_geojson) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                internal_code = str(feature['properties']['id'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=False,
                    is_latest=False,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=internal_code,
                    revision_number=2,
                    unique_code_version=2,
                    level=1,
                    parent=geo_parent,
                    layer_file=layer_file,
                    ancestor=geo_parent
                ))
                index += 1
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_parent_v1,
            revised_geographical_entity=geo_parent,
            revision_number=2
        )
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        for i in range(4):
            comparison = BoundaryComparison.objects.filter(
                main_boundary=geographical_entities[i]
            ).first()
            self.assertTrue(comparison)
            self.assertTrue(comparison.comparison_boundary)
            self.assertTrue(comparison.is_same_entity)
            self.assertEqual(comparison.main_boundary.uuid,
                             comparison.comparison_boundary.uuid)
            self.assertEqual(comparison.main_boundary.unique_code,
                             comparison.comparison_boundary.unique_code)

    def test_run_boundary_matching_ucode_split_case(self):
        dataset = DatasetF.create()
        geo_parent_v1, _ = self.setup_boundary_matching(
            dataset
        )
        geo_parent = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=2,
            level=0,
            unique_code='CODE',
            unique_code_version=2
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file = LayerFileF.create(layer_upload_session=upload_session)
        # load from entities_2 with reordered features
        entities_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entities_3.geojson')
        index = 0
        geographical_entities = []
        with open(entities_1_geojson) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                internal_code = str(feature['properties']['id'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=False,
                    is_latest=False,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=internal_code,
                    revision_number=2,
                    unique_code_version=2,
                    level=1,
                    parent=geo_parent,
                    layer_file=layer_file,
                    ancestor=geo_parent
                ))
                index += 1
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_parent_v1,
            revised_geographical_entity=geo_parent,
            revision_number=2
        )
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        # feature 0-2 should match
        for i in range(3):
            comparison = BoundaryComparison.objects.filter(
                main_boundary=geographical_entities[i]
            ).first()
            self.assertTrue(comparison)
            self.assertTrue(comparison.comparison_boundary)
            self.assertTrue(comparison.is_same_entity)
            self.assertEqual(comparison.main_boundary.uuid,
                             comparison.comparison_boundary.uuid)
            self.assertEqual(comparison.main_boundary.unique_code,
                             comparison.comparison_boundary.unique_code)
        comparison = BoundaryComparison.objects.filter(
            main_boundary=geographical_entities[3]
        ).first()
        self.assertTrue(comparison)
        self.assertTrue(comparison.comparison_boundary)
        self.assertFalse(comparison.is_same_entity)
        self.assertEqual(comparison.comparison_boundary.unique_code,
                         'CODE_0004')
        self.assertEqual(comparison.main_boundary.unique_code,
                         'CODE_0005')
        # this will not find CODE_0004 as comparison since already being used
        comparison = BoundaryComparison.objects.filter(
            main_boundary=geographical_entities[4]
        ).first()
        self.assertTrue(comparison)
        self.assertFalse(comparison.comparison_boundary)
        self.assertFalse(comparison.is_same_entity)
        self.assertEqual(comparison.main_boundary.unique_code,
                         'CODE_0006')

    def test_run_boundary_matching_ucode_merge_case(self):
        dataset = DatasetF.create()
        geo_parent_v1, _ = self.setup_boundary_matching(
            dataset
        )
        geo_parent = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=1,
            level=0,
            unique_code='CODE',
            unique_code_version=1
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file = LayerFileF.create(layer_upload_session=upload_session)
        # load from entities_2 with reordered features
        entities_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entities_4.geojson')
        index = 0
        geographical_entities = []
        with open(entities_1_geojson) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                internal_code = str(feature['properties']['id'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=False,
                    is_latest=False,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=internal_code,
                    revision_number=2,
                    unique_code_version=2,
                    level=1,
                    parent=geo_parent,
                    layer_file=layer_file,
                    ancestor=geo_parent
                ))
                index += 1
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_parent_v1,
            revised_geographical_entity=geo_parent,
            revision_number=2
        )
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        new_ucodes = [
            'CODE_0005',
            'CODE_0006',
            'CODE_0007'
        ]
        # only CODE_0002 will be found
        for i in range(4):
            comparison = BoundaryComparison.objects.filter(
                main_boundary=geographical_entities[i]
            ).first()
            if comparison.main_boundary.unique_code == 'CODE_0002':
                self.assertTrue(comparison)
                self.assertTrue(comparison.comparison_boundary)
                self.assertTrue(comparison.is_same_entity)
                self.assertEqual(comparison.main_boundary.uuid,
                                 comparison.comparison_boundary.uuid)
                self.assertEqual(comparison.main_boundary.unique_code,
                                 comparison.comparison_boundary.unique_code)
            else:
                self.assertTrue(comparison)
                self.assertTrue(comparison.comparison_boundary)
                self.assertFalse(comparison.is_same_entity)
                self.assertIn(comparison.main_boundary.unique_code,
                              new_ucodes)

    def test_run_boundary_matching_upload_level_0(self):
        dataset = DatasetF.create()
        geo_parent_v1, _ = self.setup_boundary_matching(
            dataset
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file0 = LayerFileF.create(
            layer_upload_session=upload_session,
            level=0
        )
        geo_parent = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=2,
            level=0,
            unique_code='',
            unique_code_version=None,
            layer_file=layer_file0,
            is_validated=True,
            is_approved=False,
            is_latest=False,
            internal_code=geo_parent_v1.internal_code,
            geometry=geo_parent_v1.geometry
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            level=1
        )
        # load from entities_2 with reordered features
        entities_1_geojson = absolute_path(
            'modules', 'admin_boundaries', 'tests',
            'admin_boundary_matching_data',
            'entities_2.geojson')
        index = 0
        geographical_entities = []
        with open(entities_1_geojson) as geojson:
            data = json.load(geojson)
            for feature in data['features']:
                geom_str = json.dumps(feature['geometry'])
                internal_code = str(feature['properties']['id'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=False,
                    is_latest=False,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=internal_code,
                    revision_number=2,
                    unique_code_version=2,
                    level=1,
                    parent=geo_parent,
                    layer_file=layer_file,
                    ancestor=geo_parent
                ))
                index += 1
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_parent_v1,
            revised_geographical_entity=geo_parent,
            revision_number=2
        )
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.run()
        # assert level 0
        comparison = BoundaryComparison.objects.filter(
            main_boundary=geo_parent
        ).first()
        self.assertTrue(comparison)
        self.assertTrue(comparison.comparison_boundary)
        self.assertTrue(comparison.is_same_entity)
        # assert level 1
        for i in range(4):
            comparison = BoundaryComparison.objects.filter(
                main_boundary=geographical_entities[i]
            ).first()
            self.assertTrue(comparison)
            self.assertTrue(comparison.comparison_boundary)
            self.assertTrue(comparison.is_same_entity)
            self.assertEqual(comparison.main_boundary.uuid,
                             comparison.comparison_boundary.uuid)
            self.assertEqual(comparison.main_boundary.unique_code,
                             comparison.comparison_boundary.unique_code)

    def test_generate_ucode_for_new_entities(self):
        # first_upload: create level 1 and level 2, and run ucode generation
        # should have different ucode at level 2 for each parent
        dataset = DatasetF.create()
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        layer_file0 = LayerFileF.create(
            layer_upload_session=upload_session,
            level=0
        )
        layer_file1 = LayerFileF.create(
            layer_upload_session=upload_session,
            level=1
        )
        layer_file2 = LayerFileF.create(
            layer_upload_session=upload_session,
            level=2
        )
        # create level 0 with unique code
        geo_parent = GeographicalEntityF.create(
            dataset=dataset,
            revision_number=1,
            level=0,
            unique_code='CODE',
            unique_code_version=1,
            layer_file=layer_file0,
            is_validated=True,
            is_approved=False,
            is_latest=False,
            internal_code='CODE'
        )
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            revised_entity_id='CODE',
            revised_geographical_entity=geo_parent
        )
        # create level 1 without unique code
        entities_1 = []
        for i in range(2):
            entities_1.append(GeographicalEntityF.create(
                dataset=dataset,
                revision_number=1,
                level=1,
                parent=geo_parent,
                ancestor=geo_parent,
                unique_code='',
                unique_code_version=1,
                layer_file=layer_file1,
                is_validated=True,
                is_approved=False,
                is_latest=False,
                internal_code=f'CODE{i+1}'
            ))
        entities_2 = []
        for i in range(3):
            entities_2.append(GeographicalEntityF.create(
                dataset=dataset,
                revision_number=1,
                level=2,
                parent=entities_1[0],
                ancestor=geo_parent,
                unique_code='',
                unique_code_version=1,
                layer_file=layer_file2,
                is_validated=True,
                is_approved=False,
                is_latest=False,
                internal_code=f'CODE1{i+1}'
            ))
        for i in range(2):
            entities_2.append(GeographicalEntityF.create(
                dataset=dataset,
                revision_number=1,
                level=2,
                parent=entities_1[1],
                ancestor=geo_parent,
                unique_code='',
                unique_code_version=1,
                layer_file=layer_file2,
                is_validated=True,
                is_approved=False,
                is_latest=False,
                internal_code=f'CODE2{i+1}'
            ))
        admin_boundary_matching = AdminBoundaryMatching(
            entity_upload=entity_upload
        )
        admin_boundary_matching.new_entities = (
            geo_parent.
            all_children().filter(
                layer_file__in=upload_session
                .layerfile_set.all(),
            ).order_by('level', 'internal_code')
        )
        admin_boundary_matching.generate_unique_code_for_new_entities()
        for idx, entity in enumerate(entities_1):
            updated_entity = GeographicalEntity.objects.get(id=entity.id)
            sequence_number = str(idx + 1).zfill(4)
            self.assertEqual(updated_entity.unique_code,
                             f'CODE_{sequence_number}')
        for idx in range(3):
            updated_entity = GeographicalEntity.objects.get(
                id=entities_2[idx].id
            )
            sequence_number = str(idx + 1).zfill(4)
            self.assertEqual(updated_entity.unique_code,
                             f'CODE_0001_{sequence_number}')
        for idx in range(2):
            updated_entity = GeographicalEntity.objects.get(
                id=entities_2[idx + 3].id
            )
            sequence_number = str(idx + 1).zfill(4)
            self.assertEqual(updated_entity.unique_code,
                             f'CODE_0002_{sequence_number}')
