import json
import random
from collections import OrderedDict
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from dateutil.parser import isoparse

from rest_framework.test import APIRequestFactory
from georepo.utils import absolute_path
from georepo.models import IdType, DatasetView
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    init_view_privacy_level,
    calculate_entity_count_in_view
)
from georepo.models.entity import GeographicalEntity
from georepo.utils.permission import get_view_permission_privacy_level
from georepo.utils.tile_configs import populate_tile_configs


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process(*args, **kwargs):
    return DummyTask('1')


def mocked_cache_get(self, *args, **kwargs):
    return OrderedDict()


class EntityResponseChecker(object):

    def check_response(self, item: dict, geo: GeographicalEntity,
                       excluded_columns=[], geom_type=None, user=None):
        self.assertEqual(
            item['name'],
            geo.label
        )
        self.assertEqual(
            item['ucode'],
            geo.ucode
        )
        self.assertIn(
            'concept_ucode',
            item
        )
        self.assertEqual(
            item['concept_ucode'],
            geo.concept_ucode
        )
        self.assertEqual(
            item['uuid'],
            geo.uuid_revision
        )
        self.assertEqual(
            item['concept_uuid'],
            geo.uuid
        )
        self.assertEqual(
            item['admin_level'],
            geo.level
        )
        if geo.admin_level_name:
            self.assertEqual(
                item['level_name'],
                geo.admin_level_name
            )
        else:
            self.assertNotIn(
                'level_name',
                item
            )
        self.assertEqual(
            item['type'],
            geo.type.label
        )
        self.assertEqual(
            item['start_date'],
            geo.start_date.isoformat()
        )
        if geo.end_date:
            self.assertEqual(
                item['end_date'],
                geo.end_date.isoformat()
            )
        else:
            self.assertNotIn(
                'end_date',
                item
            )
        self.assertIn('ext_codes', item)
        self.assertTrue(len(item['ext_codes'].keys()) > 0)
        self.assertEqual(
            item['ext_codes']['default'],
            geo.internal_code
        )
        entity_ids = geo.entity_ids.all()
        for entity_id in entity_ids:
            self.assertIn(
                entity_id.code.name,
                item['ext_codes']
            )
            self.assertEqual(
                item['ext_codes'][entity_id.code.name],
                entity_id.value
            )
        self.assertIn('names', item)
        self.assertEqual(len(item['names']), geo.entity_names.count())
        entity_names = geo.entity_names.order_by('idx').all()
        for entity_name in entity_names:
            name = [x for x in item['names'] if
                    x['name'] == entity_name.name]
            self.assertTrue(len(name) > 0)
            name = name[0]
            if entity_name.label:
                self.assertIn(
                    'label',
                    name
                )
                self.assertEqual(
                    entity_name.label,
                    name['label']
                )
            if entity_name.language:
                self.assertIn(
                    'lang',
                    name
                )
                self.assertEqual(
                    entity_name.language.code,
                    name['lang']
                )
        self.assertEqual(
            item['is_latest'],
            geo.is_latest
        )
        self.assertIn('parents', item)
        self.assertEqual(len(item['parents']), geo.level)
        if geo.parent:
            parent = geo.parent
            while parent:
                item_parents = [x for x in item['parents'] if
                                x['ucode'] == parent.ucode]
                self.assertEqual(len(item_parents), 1)
                item_parent = item_parents[0]
                self.assertEqual(parent.ucode, item_parent['ucode'])
                self.assertEqual(parent.internal_code, item_parent['default'])
                self.assertEqual(parent.level, item_parent['admin_level'])
                self.assertEqual(parent.type.label, item_parent['type'])
                parent = parent.parent
        self.assertIn('bbox', item)
        self.assertEqual(len(item['bbox']), 4)
        for col in excluded_columns:
            self.assertNotIn(col, item)
        if geom_type == 'centroid':
            self.assertIn('centroid', item)
        if geom_type == 'geometry':
            self.assertIn('geometry', item)
        if user:
            self.check_user_can_view_entity(item, user)

    def check_user_can_view_entity(self, item: dict, user):
        """
        Test whether user can view entity with current permission level.
        """
        self.assertIn('uuid', item)
        geo = GeographicalEntity.objects.get(uuid_revision=item['uuid'])
        max_privacy_level = get_view_permission_privacy_level(user,
                                                              geo.dataset)
        self.assertGreaterEqual(max_privacy_level, geo.privacy_level)

    def check_user_can_view_entity_in_view(self, item: dict,
                                           user, dataset_view):
        """
        Test whether user can view entity.

        This also considers external user permission in dataset_view
        """
        self.assertIn('uuid', item)
        geo = GeographicalEntity.objects.get(uuid_revision=item['uuid'])
        max_privacy_level = get_view_permission_privacy_level(
            user,
            geo.dataset,
            dataset_view=dataset_view
        )
        self.assertGreaterEqual(max_privacy_level, geo.privacy_level)


class BaseDatasetViewTest(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.entity_type0 = EntityTypeF.create(label='Country')
        self.entity_type1 = EntityTypeF.create(label='Region')
        self.dataset = DatasetF.create()
        populate_tile_configs(self.dataset.id)
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            geom = GEOSGeometry(geom_str)
            self.pak0_1 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type0,
                is_validated=True,
                is_approved=True,
                is_latest=False,
                geometry=geom,
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=1,
                start_date=isoparse('2023-01-01T06:16:13Z'),
                end_date=isoparse('2023-01-10T06:16:13Z'),
                concept_ucode='#PAK_1',
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.pak0_1,
                default=True,
                value=self.pak0_1.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.pak0_1,
                name=self.pak0_1.label,
                language=self.enLang,
                idx=0
            )
            self.pak0_2 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type0,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=geom,
                internal_code='PAK',
                revision_number=2,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=2,
                start_date=isoparse('2023-01-10T06:16:13Z'),
                uuid=self.pak0_1.uuid,
                concept_ucode=self.pak0_1.concept_ucode,
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']',
                source='ABCD'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.pak0_2,
                default=True,
                value=self.pak0_2.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.pak0_2,
                name=self.pak0_2.label,
                language=self.enLang,
                idx=0
            )
            EntityNameF.create(
                geographical_entity=self.pak0_2,
                name='pktn',
                language=self.enLang,
                idx=1
            )
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_1.geojson')
        with open(geojson_1_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entities_1 = []
            self.entities_2 = []
            entity_1_uuid = None
            entity_1_cucode = None
            v1_idx = [0, 1]
            random.shuffle(v1_idx)
            temp_entities = {}
            for i in v1_idx:
                geom = GEOSGeometry(geom_str)
                entity = GeographicalEntityF.create(
                    parent=self.pak0_1,
                    ancestor=self.pak0_1,
                    level=1,
                    admin_level_name='Region',
                    dataset=self.dataset,
                    type=self.entity_type1,
                    is_validated=True,
                    is_approved=True,
                    is_latest=False,
                    geometry=geom,
                    internal_code=f'PAK00{i+1}',
                    revision_number=1,
                    label='Khyber Pakhtunkhwa',
                    unique_code=f'PAK_000{i+1}',
                    unique_code_version=1,
                    start_date=isoparse('2023-01-01T06:16:13Z'),
                    end_date=isoparse('2023-01-10T06:16:13Z'),
                    concept_ucode=f'#PAK_{i+2}',
                    centroid=geom.point_on_surface.wkt,
                    bbox='[' + ','.join(map(str, geom.extent)) + ']'
                )
                if i == 0:
                    entity_1_uuid = entity.uuid
                    entity_1_cucode = entity.concept_ucode
                EntityIdF.create(
                    code=self.pCode,
                    geographical_entity=entity,
                    default=True,
                    value=entity.internal_code
                )
                EntityNameF.create(
                    geographical_entity=entity,
                    name=entity.label,
                    language=self.enLang,
                    idx=0
                )
                temp_entities[i] = entity
            v1_idx.sort()
            self.entities_1 = [temp_entities[i] for i in v1_idx]

            privacy_levels = [4, 3, 1]
            v2_idx = [0, 1, 2]
            random.shuffle(v2_idx)
            temp_entities2 = {}
            for i in v2_idx:
                geom = GEOSGeometry(geom_str)
                entity = GeographicalEntityF.create(
                    parent=self.pak0_2,
                    ancestor=self.pak0_2,
                    level=1,
                    admin_level_name='Region',
                    dataset=self.dataset,
                    type=self.entity_type1,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=geom,
                    internal_code=f'PAK00{i+1}',
                    revision_number=2,
                    label='Khyber Pakhtunkhwa',
                    unique_code=f'PAK_000{i+1}',
                    unique_code_version=2,
                    start_date=isoparse('2023-01-10T06:16:13Z'),
                    privacy_level=privacy_levels[i],
                    concept_ucode=f'#PAK_{i+4}',
                    centroid=geom.point_on_surface.wkt,
                    bbox='[' + ','.join(map(str, geom.extent)) + ']'
                )
                if i == 0:
                    entity.uuid = entity_1_uuid
                    entity.concept_ucode = entity_1_cucode
                    entity.save()
                EntityIdF.create(
                    code=self.pCode,
                    geographical_entity=entity,
                    default=True,
                    value=entity.internal_code
                )
                EntityNameF.create(
                    geographical_entity=entity,
                    name=entity.label,
                    language=self.enLang,
                    idx=0
                )
                temp_entities2[i] = entity
            v2_idx.sort()
            self.entities_2 = [temp_entities2[i] for i in v2_idx]
        generate_default_view_dataset_latest(self.dataset)
        self.dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(self.dataset_view)
        calculate_entity_count_in_view(self.dataset_view)


class FakeResolverMatchV1:
    """Fake class to mock versioning"""
    namespace = 'v1'
