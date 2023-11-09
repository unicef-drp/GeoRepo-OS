import json
import random
from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from dateutil.parser import isoparse

from georepo.utils import absolute_path
from georepo.models import IdType, DatasetView
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    init_view_privacy_level
)
from georepo.tasks.geocoding import (
    get_containment_check_query
)


class TestProcessGeocodingRequest(TestCase):

    def setUp(self):
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.entity_type0 = EntityTypeF.create(label='Country')
        self.entity_type1 = EntityTypeF.create(label='Region')
        self.dataset = DatasetF.create()
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
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
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

    def test_get_containment_check_query(self):
        sql, query_values = get_containment_check_query(
            self.dataset_view, 'tmp.test_table', 'ST_Intersects', 0,
            4, 'ucode', 0
        )
        self.assertIn('ST_Intersects(s.geometry, tmp_entity.geometry)', sql)
        self.assertIn('from tmp.test_table s', sql)
        self.assertIn(str(self.dataset_view.uuid), sql)
        self.assertIn(self.dataset.id, query_values)
        self.assertIn(4, query_values)