import json
import random
import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from dateutil.parser import isoparse

from georepo.utils import absolute_path
from georepo.models import (
    IdType, DatasetView
)
from georepo.models.base_task_request import (
    PENDING, DONE
)
from georepo.models.geocoding_request import (
    GeocodingRequest, GEOJSON
)
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    init_view_privacy_level
)
from georepo.tasks.geocoding import (
    get_containment_check_query,
    process_geocoding_request
)
from georepo.api_views.entity_view import (
    ViewEntityBatchGeocoding,
    ViewEntityBatchGeocodingStatus,
    ViewEntityBatchGeocodingResult
)
from georepo.utils.fiona_utils import (
    open_collection_by_file
)


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process(*args, **kwargs):
    return DummyTask('1')


class TestProcessGeocodingRequest(TestCase):

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

    @mock.patch('georepo.api_views.entity_view.'
                'process_geocoding_request.delay')
    def test_submit_batch_geocoding(self, mocked_task):
        mocked_task.side_effect = mocked_process
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': 'ST_Intersects',
            'distance': 0,
            'admin_level': 0,
            'id_type': 'ucode'
        }
        test_file_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_test_points.geojson')
        data = open(test_file_path, 'rb')
        file = SimpleUploadedFile(
            content=data.read(),
            name=data.name,
            content_type='multipart/form-data'
        )
        request = self.factory.post(
            reverse(
                'v1:batch-geocoding',
                kwargs=kwargs
            ),
            data={
                'file': file
            }
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocoding.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        mocked_task.assert_called_once()
        self.assertIn('request_id', response.data)
        self.assertIn('status_url', response.data)
        geocoding_request = GeocodingRequest.objects.filter(
            uuid=response.data['request_id']
        ).first()
        self.assertTrue(geocoding_request)
        self.assertEqual(geocoding_request.status, PENDING)
        self.assertEqual(geocoding_request.file_type, GEOJSON)
        self.assertTrue(geocoding_request.file)
        params = (
            f'({str(self.dataset_view.id)},\'ST_Intersects\','
            f'0,\'ucode\',0)'
        )
        self.assertEqual(geocoding_request.parameters, params)
        self.assertTrue(geocoding_request.task_id)
        process_geocoding_request(geocoding_request.id)
        geocoding_request.refresh_from_db()
        self.assertEqual(geocoding_request.status, DONE)
        self.assertTrue(geocoding_request.output_file)
        self.assertEqual(geocoding_request.feature_count, 3)
        status_kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'request_id': response.data['request_id']
        }
        request = self.factory.get(
            reverse(
                'v1:check-status-batch-geocoding',
                kwargs=status_kwargs
            )
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocodingStatus.as_view()
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], DONE)
        self.assertIn('output_url', response.data)
        self.assertTrue(response.data['output_url'])
        request = self.factory.get(
            reverse(
                'v1:get-result-batch-geocoding',
                kwargs=status_kwargs
            )
        )
        request.user = self.superuser
        view = ViewEntityBatchGeocodingResult.as_view()
        response = view(request, **status_kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertTrue(response.has_header('Content-Type'))
        # check for output result
        with geocoding_request.output_file.open('rb') as json_data:
            features = json.load(json_data)
            self.assertEqual(len(features['features']), 3)
            feat_1 = features['features'][0]
            self.assertIn('ucode', feat_1['properties'])
            self.assertEqual(len(feat_1['properties']['ucode']), 1)
            self.assertEqual(feat_1['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_2 = features['features'][1]
            self.assertIn('ucode', feat_2['properties'])
            self.assertEqual(len(feat_2['properties']['ucode']), 1)
            self.assertEqual(feat_2['properties']['ucode'][0],
                             self.pak0_2.ucode)
            feat_3 = features['features'][2]
            self.assertIn('ucode', feat_3['properties'])
            self.assertEqual(len(feat_3['properties']['ucode']), 0)
