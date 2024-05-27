import uuid
import mock
import json
from dateutil.parser import isoparse
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.test import APIRequestFactory
from rest_framework import versioning

from georepo.utils import absolute_path
from georepo.models import IdType, GeographicalEntity, EntityType
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF
)
from georepo.api_views.entity import (
    EntityBoundingBox,
    EntityIdList,
    EntityContainmentCheck,
    EntityFuzzySearch,
    EntityGeometryFuzzySearch,
    EntityList,
    FindEntityById,
    FindEntityVersionsByConceptUCode,
    EntityListByUCode,
    EntityListByAdminLevel,
    EntityListByAdminLevelAndUCode,
    FindEntityVersionsByUCode
)
from georepo.tests.common import (
    EntityResponseChecker,
    FakeResolverMatchV1
)


class TestApiEntity(EntityResponseChecker, TestCase):

    def setUp(self) -> None:
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanist'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.entity_type = EntityTypeF.create(label='Country')
        self.dataset = DatasetF.create()
        self.entity = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=self.entity_type,
            level=0,
            dataset=self.dataset,
            internal_code='GO',
            label='GO',
            is_approved=True,
            is_latest=True,
            unique_code='GO',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#GO_1'
        )
        self.factory = APIRequestFactory()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            geom = GEOSGeometry(geom_str)
            self.geographical_entity = GeographicalEntityF.create(
                dataset=self.dataset,
                type=self.entity_type,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=geom,
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                start_date=isoparse('2023-01-01T06:16:13Z'),
                concept_ucode='#PAK_1',
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.geographical_entity,
                default=True,
                value=self.geographical_entity.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name=self.geographical_entity.label,
                language=self.enLang,
                idx=0
            )
            EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name='only paktang',
                default=False,
                language=self.esLang,
                idx=1
            )

    def test_get_entity_list(self):
        dataset = DatasetF.create()
        entity_type0 = EntityType.objects.get_by_label('Country')
        entity_type1 = EntityType.objects.get_by_label('Region')
        parent = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=entity_type0,
            level=0,
            dataset=dataset,
            unique_code='PAK0',
            unique_code_version=1,
            internal_code='PAK0',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_1'
        )
        geo = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=entity_type1,
            level=1,
            dataset=dataset,
            parent=parent,
            ancestor=parent,
            internal_code='PAK0001',
            unique_code='PAK_0001',
            unique_code_version=1,
            geometry=self.geographical_entity.geometry,
            is_approved=True,
            is_latest=True,
            admin_level_name='Province',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_2',
            centroid=self.geographical_entity.centroid,
            bbox=self.geographical_entity.bbox
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=geo,
            default=True,
            value=geo.internal_code
        )
        EntityNameF.create(
            geographical_entity=geo,
            name=geo.label,
            language=self.enLang,
            default=True,
            idx=0
        )
        geo = GeographicalEntity.objects.get(id=geo.id)
        kwargs = {
            'uuid': dataset.uuid,
            'entity_type': entity_type1.label.lower()
        }
        scheme = versioning.NamespaceVersioning
        view = EntityList.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse('v1:search-entity-by-type', kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0], geo,
                            excluded_columns=['centroid', 'geometry'])

        # test search by entity_type+ucode
        kwargs = {
            'uuid': dataset.uuid,
            'entity_type': entity_type1.label,
            'ucode': f'{parent.unique_code}_V1'
        }
        scheme = versioning.NamespaceVersioning
        view = EntityListByUCode.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-type-and-ucode',
                kwargs=kwargs
            ) + '/?cached=False'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0], geo,
                            excluded_columns=['centroid', 'geometry'])
        # fetch as geojson
        kwargs = {
            'uuid': dataset.uuid,
            'entity_type': entity_type1.label,
            'ucode': f'{parent.unique_code}_V1'
        }
        scheme = versioning.NamespaceVersioning
        view = EntityListByUCode.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-type-and-ucode',
                kwargs=kwargs
            ) + '/?cached=False&format=geojson'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['features']), 1)
        self.assertTrue(response.has_header('page'))
        self.assertTrue(response.has_header('page_size'))
        self.assertTrue(response.has_header('total_page'))

    def test_get_entity_list_by_admin_level(self):
        dataset = DatasetF.create()
        entity_type0 = EntityType.objects.get_by_label('Country')
        entity_type1 = EntityType.objects.get_by_label('Region')
        parent = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=entity_type0,
            level=0,
            dataset=dataset,
            unique_code='PAK0',
            unique_code_version=1,
            internal_code='PAK0',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_1'
        )
        geo = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=entity_type1,
            level=1,
            dataset=dataset,
            parent=parent,
            ancestor=parent,
            internal_code='PAK0001',
            unique_code='PAK_0001',
            unique_code_version=1,
            geometry=self.geographical_entity.geometry,
            is_approved=True,
            is_latest=True,
            admin_level_name='Province',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_2',
            centroid=self.geographical_entity.centroid,
            bbox=self.geographical_entity.bbox
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=geo,
            default=True,
            value=geo.internal_code
        )
        EntityNameF.create(
            geographical_entity=geo,
            name=geo.label,
            language=self.enLang,
            default=True,
            idx=0
        )
        geo = GeographicalEntity.objects.get(id=geo.id)
        kwargs = {
            'uuid': dataset.uuid,
            'admin_level': 1
        }
        scheme = versioning.NamespaceVersioning
        view = EntityListByAdminLevel.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse('v1:search-entity-by-level', kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0], geo,
                            excluded_columns=['centroid', 'geometry'])
        # test search by admin_level+ucode
        kwargs = {
            'uuid': dataset.uuid,
            'admin_level': 1,
            'ucode': f'{parent.unique_code}_V1'
        }
        scheme = versioning.NamespaceVersioning
        view = EntityListByAdminLevelAndUCode.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-level-and-ucode',
                kwargs=kwargs
            ) + '/?cached=False&geom=centroid'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0], geo,
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def test_entity_bounding_box(self):
        # found is_approved and is_latest
        pcode_0 = 'PAK'
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'PCode',
            'id': pcode_0
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        # pcode is not found
        pcode_1 = 'PAK123'
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'PCode',
            'id': pcode_1
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'otherID',
            'id': pcode_1
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.data), 1)
        # entity is not approved yet
        entity = GeographicalEntityF.create(
            level=0,
            uuid=str(uuid.uuid4()),
            uuid_revision=str(uuid.uuid4()),
            dataset=self.dataset,
            is_latest=True,
            is_approved=False,
            label='Test',
            revision_number=1,
            internal_code='ABC',
            concept_ucode='#ABC_1'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'PCode',
            'id': entity.internal_code
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.data), 1)
        # pcode has multiple records, should get the recent one
        geojson_0_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_1.geojson')
        with open(geojson_0_1_path) as geojson:
            data = json.load(geojson)
        geom_str = json.dumps(data['features'][0]['geometry'])
        geom = GEOSGeometry(geom_str)
        entity = GeographicalEntityF.create(
            level=0,
            uuid=str(uuid.uuid4()),
            uuid_revision=str(uuid.uuid4()),
            dataset=self.dataset,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            geometry=geom,
            internal_code='PAK',
            revision_number=1,
            concept_ucode='#PAK_1',
            centroid=geom.point_on_surface.wkt,
            bbox='[' + ','.join(map(str, geom.extent)) + ']'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'PCode',
            'id': entity.internal_code
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0], entity.geometry.extent[0])
        self.assertEqual(response.data[3], entity.geometry.extent[3])
        self.assertNotEqual(
            response.data[0],
            self.geographical_entity.geometry.extent[0]
        )
        self.assertNotEqual(
            response.data[3],
            self.geographical_entity.geometry.extent[3]
        )
        # search using UUID
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'id_type': 'uuid',
            'id': entity.uuid_revision
        }
        request = self.factory.get(
            reverse('v1:entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0], entity.geometry.extent[0])
        self.assertEqual(response.data[3], entity.geometry.extent[3])

    def test_containment_check(self):
        # geojson data
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_1.geojson')
        with open(geojson_1_path) as geojson:
            data_1 = json.load(geojson)
        geojson_2_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_2.geojson')
        with open(geojson_2_path) as geojson:
            data_2 = json.load(geojson)
        geojson_3_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_3.geojson')
        with open(geojson_3_path) as geojson:
            data_3 = json.load(geojson)
        # ST_Intersects
        level_0 = 'Country'
        spatial_query_0 = 'ST_Intersects'
        kwargs = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_0,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')
        # no intersects
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_2,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('PCode', response.data['features'][0]['properties'])
        # within, not found
        spatial_query_2 = 'ST_Within'
        kwargs = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_2,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('PCode', response.data['features'][0]['properties'])
        # within found
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')
        # dwithin
        spatial_query_3 = 'ST_DWithin'
        spatial_distance = 1
        kwargs = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_3,
            'distance': spatial_distance,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_2,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')
        # ST_Within(ST_Centroid)
        spatial_query_4 = 'ST_Within(ST_Centroid)'
        kwargs = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_4,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')
        # bad request
        spatial_query_5 = 'ST_Intersects'
        level_0_error = 'countrytest'
        kwargs_error = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_5,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs_error
            ) + f'/?entity_type={level_0_error}',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs_error)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)
        # return hierarchy data in response
        spatial_query_2 = 'ST_Within'
        kwargs = {
            'uuid': self.dataset.uuid,
            'spatial_query': spatial_query_2,
            'distance': 0,
            'id_type': 'ucode'
        }
        request = self.factory.post(
            reverse(
                'v1:entity-containment-check',
                kwargs=kwargs
            ),
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = EntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('ucode', response.data['features'][0]['properties'])

    def test_entity_id_list(self):
        request = self.factory.get(
            reverse('v1:id-type-list')
        )
        request.user = self.superuser
        view = EntityIdList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 7)
        self.assertIn('PCode', response.data)
        self.assertIn('uuid', response.data)

    def test_entity_fuzzy_search(self):
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'search_text': 'paktan'
        }
        request = self.factory.get(
            reverse('v1:entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # test when 1 entity has two names (Pakistan and only paktang),
        # then only pull the name
        # with the highest similarity
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.geographical_entity,
                            excluded_columns=['centroid', 'geometry'])
        entity_2 = GeographicalEntityF.create(
            dataset=self.dataset,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK',
            revision_number=2,
            label='Pakistan',
            unique_code='PAK1',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK_2',
            bbox='[1,1,1,1]'
        )
        EntityNameF.create(
            geographical_entity=entity_2,
            name=entity_2.label,
            idx=0
        )
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'search_text': 'paki'
        }
        request = self.factory.get(
            reverse('v1:entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # search with paki, should return two diff results
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == entity_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            entity_2,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.geographical_entity.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.geographical_entity,
                            excluded_columns=['centroid', 'geometry'])
        # simulate empty name, should return 200 and empty result
        dataset_2 = DatasetF.create(
            module=self.dataset.module
        )
        GeographicalEntityF.create(
            dataset=dataset_2,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK',
            revision_number=1,
            label='Pakistan',
            unique_code='PAK1',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK_10',
            bbox='[1,1,1,1]'
        )
        kwargs = {
            'uuid': str(dataset_2.uuid),
            'search_text': 'paki'
        }
        request = self.factory.get(
            reverse('v1:entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        request.user = self.superuser
        view = EntityFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

    @mock.patch.object(
        EntityGeometryFuzzySearch, 'get_simplify_tolerance',
        mock.Mock(return_value=0.08))
    def test_entity_fuzzy_search_geom(self):
        # geojson data
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_1_path) as geojson:
            data_1 = json.load(geojson)
        kwargs = {
            'uuid': str(self.dataset.uuid)
        }
        request = self.factory.post(
            reverse(
                'v1:entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = EntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.geographical_entity,
                            excluded_columns=['centroid', 'geometry'])
        # invalid geojson
        request = self.factory.post(
            reverse(
                'v1:entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data={},
            format='json'
        )
        request.user = self.superuser
        view = EntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        # search with level=2, return empty result
        request = self.factory.post(
            reverse(
                'v1:entity-fuzzy-search-by-geometry', kwargs=kwargs
            ) + '?admin_level=2',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = EntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_entity_by_id(self):
        dataset = DatasetF.create()
        entity_type0 = EntityType.objects.get_by_label('Country')
        entity_type1 = EntityType.objects.get_by_label('Region')
        parent = GeographicalEntityF.create(
            uuid=uuid.uuid4(),
            type=entity_type0,
            level=0,
            dataset=dataset,
            unique_code='PAK0',
            internal_code='PAK0',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_1'
        )
        geo = GeographicalEntityF.create(
            uuid=uuid.uuid4(),
            type=entity_type1,
            level=1,
            dataset=dataset,
            parent=parent,
            internal_code='PAK0001',
            unique_code='PAK_0001',
            unique_code_version=1,
            geometry=self.geographical_entity.geometry,
            is_approved=True,
            is_latest=True,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_2',
            centroid=self.geographical_entity.centroid,
            bbox=self.geographical_entity.bbox
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=geo,
            default=True,
            value=geo.internal_code
        )
        EntityNameF.create(
            geographical_entity=geo,
            name=geo.label,
            language=self.enLang,
            default=True,
            idx=0
        )
        geo = GeographicalEntity.objects.get(id=geo.id)
        # search by PCode
        kwargs = {
            'uuid': dataset.uuid,
            'id_type': self.pCode.name,
            'id': geo.internal_code
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityById.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse('v1:search-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        request.resolver_match = FakeResolverMatchV1
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            geo,
                            excluded_columns=['centroid', 'geometry'])
        # search by ucode
        kwargs = {
            'uuid': dataset.uuid,
            'id_type': 'ucode',
            'id': geo.unique_code + '_V1'
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityById.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse('v1:search-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        request.resolver_match = FakeResolverMatchV1
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            geo,
                            excluded_columns=['centroid', 'geometry'])
        # search by invalid uuid
        kwargs = {
            'uuid': dataset.uuid,
            'id_type': 'uuid',
            'id': geo.unique_code + '_V1'
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityById.as_view(versioning_class=scheme)
        request = self.factory.get(
            reverse('v1:search-entity-by-id', kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_entity_by_concept_uuid(self):
        dataset = DatasetF.create()
        entity_type0 = EntityType.objects.get_by_label('Country')
        entity_type1 = EntityType.objects.get_by_label('Region')
        parent = GeographicalEntityF.create(
            uuid=uuid.uuid4(),
            type=entity_type0,
            level=0,
            dataset=dataset,
            unique_code='PAK0',
            internal_code='PAK0',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK0_1'
        )
        geo_1 = GeographicalEntityF.create(
            uuid=uuid.uuid4(),
            type=entity_type1,
            level=1,
            dataset=dataset,
            parent=parent,
            internal_code='PAK0001',
            unique_code='PAK_0001',
            unique_code_version=1,
            geometry=self.geographical_entity.geometry,
            is_approved=True,
            is_latest=False,
            revision_number=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='#PAK0_2',
            centroid=self.geographical_entity.centroid,
            bbox=self.geographical_entity.bbox
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=geo_1,
            default=True,
            value=geo_1.internal_code
        )
        EntityNameF.create(
            geographical_entity=geo_1,
            name=geo_1.label,
            language=self.enLang,
            default=True,
            idx=0
        )
        geo_2 = GeographicalEntityF.create(
            uuid=geo_1.uuid,
            type=entity_type1,
            level=1,
            dataset=dataset,
            parent=parent,
            internal_code='PAK0001',
            unique_code='PAK_0001',
            unique_code_version=2,
            geometry=self.geographical_entity.geometry,
            is_approved=True,
            is_latest=True,
            revision_number=2,
            start_date=isoparse('2023-01-10T06:16:13Z'),
            end_date=None,
            concept_ucode=geo_1.concept_ucode,
            centroid=self.geographical_entity.centroid,
            bbox=self.geographical_entity.bbox
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=geo_2,
            default=True,
            value=geo_2.internal_code
        )
        EntityNameF.create(
            geographical_entity=geo_2,
            name=geo_2.label,
            language=self.enLang,
            default=True,
            idx=0
        )
        # search by concept ucode
        kwargs = {
            'uuid': str(dataset.uuid),
            'concept_ucode': str(geo_1.concept_ucode)
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityVersionsByConceptUCode.as_view(
            versioning_class=scheme
        )
        request = self.factory.get(
            reverse('v1:search-entity-versions-by-concept-ucode',
                    kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == geo_1.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            geo_1,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == geo_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            geo_2,
                            excluded_columns=['centroid', 'geometry'])
        # search by ucode
        kwargs = {
            'uuid': str(dataset.uuid),
            'ucode': f'{geo_1.unique_code}_V{geo_1.unique_code_version}'
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        request = self.factory.get(
            reverse('v1:search-entity-versions-by-ucode', kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == geo_1.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            geo_1,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == geo_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            geo_2,
                            excluded_columns=['centroid', 'geometry'])
        # search by timestamp
        kwargs = {
            'uuid': str(dataset.uuid),
            'ucode': f'{geo_2.unique_code}_V{geo_2.unique_code_version}'
        }
        scheme = versioning.NamespaceVersioning
        view = FindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        request = self.factory.get(
            reverse(
                'v1:search-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-07T06:16:13Z'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            geo_1,
                            excluded_columns=['centroid', 'geometry'])
        # search by timestamp should find v2
        kwargs = {
            'uuid': str(dataset.uuid),
            'ucode': f'{geo_1.unique_code}_V{geo_1.unique_code_version}'
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-18T06:16:13Z'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            geo_2,
                            excluded_columns=['centroid', 'geometry'])
        # search by timestamp should be no match
        kwargs = {
            'uuid': str(dataset.uuid),
            'ucode': f'{geo_2.unique_code}_V{geo_2.unique_code_version}'
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=1672120011'
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
