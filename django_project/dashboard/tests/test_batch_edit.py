import json
import random
import mock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry
from dateutil.parser import isoparse
from georepo.utils import absolute_path
from georepo.models import IdType
from georepo.models.base_task_request import (
    PENDING,
    DONE
)
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from dashboard.models.batch_edit import BatchEntityEdit
from dashboard.tools.entity_edit import (
    CSVBatchEntityEditImporter,
    ExcelBatchEntityEditImporter
)


class TestBatchEdit(TestCase):

    def setUp(self) -> None:
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanish'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.id_1 = IdType.objects.create(name='id_1')
        self.id_2 = IdType.objects.create(name='id_2')
        self.entity_type0 = EntityTypeF.create(label='Country')
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
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_1.geojson')
        with open(geojson_1_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entities_1 = []
            self.entities_2 = []
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

    def test_import_csv(self):
        pass

    def test_import_excel(self):
        pass
