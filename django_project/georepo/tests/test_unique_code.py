import uuid
import mock
from django.test import TestCase
from core.models.preferences import SitePreferences
from georepo.tests.model_factories import (
    GeographicalEntity,
    GeographicalEntityF,
    DatasetF
)
from dashboard.tests.model_factories import (
    BoundaryComparisonF
)
from georepo.utils.unique_code import (
    generate_unique_code,
    generate_unique_code_version,
    parse_unique_code,
    get_unique_code,
    generate_upload_unique_code_version,
    generate_unique_code_from_comparison,
    count_max_unique_code,
    generate_concept_ucode_base,
    generate_concept_ucode
)


def mocked_site_perferences(*args, **kwargs):
    p = SitePreferences()
    p.short_code_exclusion = 'ABC'
    return p


class TestUniqueCodeGeneration(TestCase):

    def test_generate_unique_code(self):
        dataset = DatasetF.create()
        entity = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO'
        )
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            parent=entity
        )
        entity_3 = GeographicalEntityF.create(
            dataset=dataset,
            parent=entity_2
        )
        generate_unique_code(entity_3)
        self.assertEqual(entity_2.unique_code, 'ISO_0001')
        self.assertEqual(entity_3.unique_code, 'ISO_0001_0001')

    def test_generate_unique_code_version(self):
        dataset = DatasetF.create()
        entity = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-10-10'
        )
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2003-10-10'
        )
        generate_unique_code_version(entity_2)
        self.assertEqual(GeographicalEntity.objects.get(
            id=entity.id
        ).unique_code_version, 1.0)

        entity_3 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-11-10'
        )
        generate_unique_code_version(entity_3)
        self.assertEqual(GeographicalEntity.objects.get(
            id=entity_3.id
        ).unique_code_version, 1.5)

        entity_4 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2005-11-10'
        )
        generate_unique_code_version(entity_4)
        self.assertEqual(GeographicalEntity.objects.get(
            id=entity_4.id
        ).unique_code_version, 3.0)

        entity_5 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-11-12'
        )
        generate_unique_code_version(entity_5)
        self.assertEqual(GeographicalEntity.objects.get(
            id=entity_5.id
        ).unique_code_version, 1.75)

        entity_0 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='1999-11-12'
        )
        generate_unique_code_version(entity_0)
        self.assertEqual(GeographicalEntity.objects.get(
            id=entity_0.id
        ).unique_code_version, 0.5)

    def test_generate_upload_unique_code_version(self):
        dataset = DatasetF.create()
        entity = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-10-10',
            unique_code_version=1.0,
            is_approved=True
        )

        version = generate_upload_unique_code_version(
            dataset,
            '2002-10-10'
        )
        self.assertEqual(version, 1.0)
        version = generate_upload_unique_code_version(
            dataset,
            '2003-10-10',
            entity
        )
        self.assertEqual(version, 2.0)
        # entity_v2
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2003-10-10',
            unique_code_version=2.0,
            is_approved=True
        )
        version = generate_upload_unique_code_version(
            dataset,
            '2002-11-10',
            entity
        )
        self.assertEqual(version, 1.5)
        # entity_v1_5
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-11-10',
            unique_code_version=1.5,
            is_approved=True
        )
        version = generate_upload_unique_code_version(
            dataset,
            '2005-11-10',
            entity
        )
        self.assertEqual(version, 3.0)
        # entity_v3
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2005-11-10',
            unique_code_version=3.0,
            is_approved=True
        )
        version = generate_upload_unique_code_version(
            dataset,
            '2002-11-12',
            entity
        )
        self.assertEqual(version, 1.75)
        # entity_v1_75
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            start_date='2002-11-12',
            unique_code_version=1.75,
            is_approved=True
        )
        version = generate_upload_unique_code_version(
            dataset,
            '1999-11-12',
            entity
        )
        self.assertEqual(version, 0.5)

    def test_parse_unique_code(self):
        unique_code = 'ISO_0001_V1'
        code, version = parse_unique_code(unique_code)
        self.assertEqual(code, 'ISO_0001')
        self.assertEqual(version, 1)
        unique_code = 'ISO_0001_V1.5'
        code, version = parse_unique_code(unique_code)
        self.assertEqual(code, 'ISO_0001')
        self.assertEqual(version, 1.5)
        unique_code = 'ISO_0001_0001_V1.75'
        code, version = parse_unique_code(unique_code)
        self.assertEqual(code, 'ISO_0001_0001')
        self.assertEqual(version, 1.75)
        # test parse error
        with self.assertRaises(ValueError) as context:
            unique_code = 'ISO'
            code, version = parse_unique_code(unique_code)
            self.assertIn(f'Invalid ucode {unique_code}: '
                          'Code should consist of unique code and '
                          'version number', str(context.exception))
        with self.assertRaises(ValueError) as context:
            unique_code = 'ISO_0001_v1.5'
            code, version = parse_unique_code(unique_code)
            self.assertIn(f'Invalid ucode {unique_code}: '
                          'V in version should be uppercase',
                          str(context.exception))
        with self.assertRaises(ValueError) as context:
            unique_code = 'ISO_0001_Vaaa'
            code, version = parse_unique_code(unique_code)
            self.assertIn(f'Invalid ucode {unique_code}: '
                          'version number must be numeric',
                          str(context.exception))

    def test_get_unique_code(self):
        code = 'ISO_0001'
        version = 1
        unique_code = get_unique_code(code, version)
        self.assertEqual(unique_code, 'ISO_0001_V1')
        code = 'ISO_0001'
        version = 1.75
        unique_code = get_unique_code(code, version)
        self.assertEqual(unique_code, 'ISO_0001_V1.75')
        code = 'ISO_0001'
        version = 0.500
        unique_code = get_unique_code(code, version)
        self.assertEqual(unique_code, 'ISO_0001_V0.5')
        code = 'ISO_0001_0001'
        version = 200
        unique_code = get_unique_code(code, version)
        self.assertEqual(unique_code, 'ISO_0001_0001_V200')

    def test_generate_unique_code_with_prefix(self):
        dataset = DatasetF.create(
            short_code='ABC'
        )
        entity = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            level=0
        )
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            parent=entity,
            level=1
        )
        entity_3 = GeographicalEntityF.create(
            dataset=dataset,
            parent=entity_2,
            level=2
        )
        generate_unique_code(entity_3)
        self.assertEqual(entity_2.unique_code, 'ABC_ISO_0001')
        self.assertEqual(entity_3.unique_code, 'ABC_ISO_0001_0001')

    def test_generate_unique_code_from_comparison(self):
        dataset = DatasetF.create(
            short_code='ABC'
        )
        entity_1 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            unique_code='ISO',
            level=0
        )
        entity = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO1',
            unique_code='ISO_0001',
            start_date='2002-10-10',
            level=1,
            parent=entity_1
        )
        generate_unique_code_from_comparison(entity_1, None)
        self.assertEqual(entity_1.unique_code, 'ABC_ISO')
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            level=1,
            parent=entity_1
        )
        # same level and parent, should reuse
        generate_unique_code_from_comparison(entity_2, entity)
        self.assertEqual(entity_2.unique_code, 'ABC_ISO_0001')
        entity_3 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            level=2,
            parent=entity_2
        )
        # different level, should not reuse
        generate_unique_code_from_comparison(entity_3, entity)
        self.assertEqual(entity_3.unique_code, '')

    def test_count_max_unique_code(self):
        dataset = DatasetF.create()
        parent = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            unique_code='ISO',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=0,
            uuid=str(uuid.uuid4())
        )
        max_count = count_max_unique_code(dataset, 1, parent)
        self.assertEqual(max_count, 0)
        entity_1 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent,
            ancestor=parent
        )
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0002',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent,
            ancestor=parent
        )
        max_count = count_max_unique_code(dataset, 1, parent)
        self.assertEqual(max_count, 2)
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0001',
            unique_code_version=2.0,
            revision_number=2,
            is_approved=True,
            level=1,
            uuid=entity_1.uuid,
            parent=parent,
            ancestor=parent
        )
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0002',
            unique_code_version=2.0,
            revision_number=2,
            is_approved=True,
            level=1,
            uuid=entity_2.uuid,
            parent=parent,
            ancestor=parent
        )
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='ISO_0003',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent,
            ancestor=parent
        )
        parent_2 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='PAK',
            unique_code='PAK',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=0,
            uuid=str(uuid.uuid4())
        )
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='PAK_0001',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent_2,
            ancestor=parent_2
        )
        GeographicalEntityF.create(
            dataset=dataset,
            unique_code='PAK_0002',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent_2,
            ancestor=parent_2
        )
        max_count = count_max_unique_code(dataset, 1, parent)
        self.assertEqual(max_count, 3)
        max_count = count_max_unique_code(dataset, 1, parent_2)
        self.assertEqual(max_count, 2)

    @mock.patch('core.models.preferences.SitePreferences.preferences')
    def test_generate_concept_ucode_base(self, perferences):
        dataset = DatasetF.create(
            short_code='ABC'
        )
        entity = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            level=0
        )
        cucode = generate_concept_ucode_base(entity, '1')
        self.assertEqual(cucode, '#ABC_ISO_1')
        # set short_code_exclusion with 'ABC'
        perferences.side_effect = mocked_site_perferences
        cucode = generate_concept_ucode_base(entity, '1')
        self.assertEqual(cucode, '#ISO_1')

    def test_generate_concept_ucode(self):
        dataset = DatasetF.create(
            short_code='ABC'
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            unique_code='ISO',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=False,
            level=0,
            uuid=str(uuid.uuid4())
        )
        parent_boundary = BoundaryComparisonF.create(
            main_boundary=parent
        )
        entity_1 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO_0001',
            unique_code='ISO_0001',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=False,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent,
            ancestor=parent
        )
        BoundaryComparisonF.create(
            main_boundary=entity_1
        )
        entity_2 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO_0002',
            unique_code='ISO_0002',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=False,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent,
            ancestor=parent
        )
        BoundaryComparisonF.create(
            main_boundary=entity_2
        )
        new_entities = parent.all_children().order_by(
            'level',
            'internal_code'
        )
        generate_concept_ucode(parent, new_entities)
        updated = GeographicalEntity.objects.get(id=parent.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_1')
        updated = GeographicalEntity.objects.get(id=entity_1.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_2')
        updated = GeographicalEntity.objects.get(id=entity_2.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_3')
        parent_0 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO',
            unique_code='ISO',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=0,
            uuid=parent.uuid,
            concept_ucode='#ABC_ISO_1'
        )
        # update parent to use same entity
        parent_boundary.comparison_boundary = parent_0
        parent_boundary.is_same_entity = True
        parent_boundary.save()
        entity_0 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO_0003',
            unique_code='ISO_0003',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=True,
            level=1,
            uuid=str(uuid.uuid4()),
            parent=parent_0,
            ancestor=parent_0,
            concept_ucode='#ABC_ISO_2'
        )
        entity_3 = GeographicalEntityF.create(
            dataset=dataset,
            internal_code='ISO_0003',
            unique_code='ISO_0003',
            unique_code_version=1.0,
            revision_number=1,
            is_approved=False,
            level=1,
            uuid=entity_0.uuid,
            parent=parent,
            ancestor=parent
        )
        BoundaryComparisonF.create(
            main_boundary=entity_3,
            comparison_boundary=entity_0,
            is_same_entity=True
        )
        new_entities = parent.all_children().order_by(
            'level',
            'internal_code'
        )
        generate_concept_ucode(parent, new_entities)
        updated = GeographicalEntity.objects.get(id=parent.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_1')
        updated = GeographicalEntity.objects.get(id=entity_1.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_3')
        updated = GeographicalEntity.objects.get(id=entity_2.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_4')
        updated = GeographicalEntity.objects.get(id=entity_3.id)
        self.assertEqual(updated.concept_ucode, '#ABC_ISO_2')
