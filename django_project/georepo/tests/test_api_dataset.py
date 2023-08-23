import uuid
import mock
import json
import io
import zipfile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.test import APIRequestFactory
from rest_framework import versioning
from rest_framework.authtoken.models import Token
from core.models.token_detail import CustomApiKey
from georepo.utils import absolute_path
from georepo.api_views.dataset import (
    DatasetDetail,
    DatasetEntityListHierarchical,
    DatasetExportDownload,
    DatasetExportDownloadByLevel,
    DatasetExportDownloadByCountry,
    DatasetExportDownloadByCountryAndLevel
)
from georepo.api_views.protected_api import IsDatasetAllowedAPI
from georepo.models import IdType, DatasetViewResource
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest
)
from georepo.utils.permission import (
    grant_dataset_viewer,
    grant_datasetview_viewer
)
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, UserF,
    EntityIdF, EntityNameF, LanguageF, IdTypeF, DatasetAdminLevelNameF
)


class FakeResolverMatchV1:
    """Fake class to mock versioning"""
    namespace = 'v1'


def mocked_set_cache(cache_key, allowed, redis_time_cache):
    return True


def mocked_get_cache(cache_key):
    return None


class TestApiDataset(TestCase):

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
            unique_code='GO'
        )
        self.factory = APIRequestFactory()
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geographical_entity = GeographicalEntityF.create(
                dataset=self.dataset,
                type=self.entity_type,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK'
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
                language=self.enLang
            )
            EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name='only paktang',
                default=False,
                language=self.esLang
            )
        self.latest_views = generate_default_view_dataset_latest(
            self.dataset
        )

    def check_disabled_module(self, view, request, kwargs=None):
        # disable module, should return 404
        self.dataset.module.is_active = False
        self.dataset.module.save()
        if kwargs:
            response = view(request, **kwargs)
        else:
            response = view(request)
        self.assertEqual(response.status_code, 404)
        self.dataset.module.is_active = True
        self.dataset.module.save()


    @mock.patch('georepo.api_views.protected_api.cache.get',
                mock.Mock(side_effect=mocked_get_cache))
    @mock.patch('georepo.api_views.protected_api.cache.set',
                mock.Mock(side_effect=mocked_set_cache))
    def test_is_dataset_allowed_api(self):
        user = UserF.create(username='test')
        token = Token.objects.create(user=user)
        dataset_view = self.latest_views[0]
        # grant viewer access with level 2
        grant_dataset_viewer(self.dataset, user, 2)
        grant_datasetview_viewer(dataset_view, user)
        resource3 = DatasetViewResource.objects.filter(
            dataset_view=dataset_view,
            privacy_level=3
        ).first()
        # without CustomAPIKey, should be 403
        request = self.factory.post(
            reverse('dataset-allowed-api') +
            f'?token={str(user.auth_token)}' +
            f'&request_url=/t/{str(resource3.uuid)}/'
        )
        view = IsDatasetAllowedAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        key = CustomApiKey(
            token_ptr=token,
            user=user,
        )
        key.save_base(raw=True)
        # Without request url
        request = self.factory.post(
            reverse('dataset-allowed-api') +
            f'?token={str(user.auth_token)}'
        )
        view = IsDatasetAllowedAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        # should not allow to access level 3
        request = self.factory.post(
            reverse('dataset-allowed-api') +
            f'?token={str(user.auth_token)}' +
            f'&request_url=/t/{str(resource3.uuid)}/'
        )
        view = IsDatasetAllowedAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        # should not allow to access level 3
        resource3 = DatasetViewResource.objects.filter(
            dataset_view=dataset_view,
            privacy_level=3
        ).first()
        request = self.factory.post(
            reverse('dataset-allowed-api') +
            f'?token={str(user.auth_token)}' +
            f'&request_url=/t/{str(resource3.uuid)}/'
        )
        view = IsDatasetAllowedAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        # should allow to access level 2
        resource2 = DatasetViewResource.objects.filter(
            dataset_view=dataset_view,
            privacy_level=2
        ).first()
        request = self.factory.post(
            reverse('dataset-allowed-api') +
            f'?token={str(user.auth_token)}' +
            f'&request_url=/t/{str(resource2.uuid)}/'
        )
        view = IsDatasetAllowedAPI.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.check_disabled_module(view, request)

    def test_get_dataset_detail(self):
        entity_type = EntityTypeF.create(label='Sub district')
        DatasetAdminLevelNameF.create(
            dataset=self.dataset,
            level=0,
            label='Country'
        )
        DatasetAdminLevelNameF.create(
            dataset=self.dataset,
            level=1,
            label='Province'
        )
        geo = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            type=entity_type,
            level=1,
            dataset=self.dataset,
            internal_code='GO_001',
            label='GO_001',
            is_approved=True,
            is_latest=True
        )
        id_type = IdTypeF.create(
            name='TCODE'
        )
        EntityIdF.create(
            code=id_type,
            geographical_entity=geo
        )
        kwargs = {
            'uuid': self.dataset.uuid
        }
        request = self.factory.get(
            reverse('v1:dataset-detail', kwargs=kwargs)
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        view = DatasetDetail.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['dataset_levels']), 2)
        #  find level 1
        level1 = [lv for lv in response.data['dataset_levels'] if
                  lv['level'] == 1][0]
        if 'url' in level1:
            self.assertNotIn(' ', level1['url'])
        # assert TCODE in id_types
        self.assertIn('possible_id_types', response.data)
        self.assertIn('TCODE', response.data['possible_id_types'])
        self.assertIn('ucode', response.data['possible_id_types'])
        self.assertIn('uuid', response.data['possible_id_types'])
        self.assertIn('concept_uuid', response.data['possible_id_types'])
        self.check_disabled_module(view, request, kwargs=kwargs)

    def test_get_hierarchical_data(self):
        geo = GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            level=1,
            dataset=self.dataset,
            unique_code='GO_001',
            parent=self.entity,
            is_approved=True,
            is_latest=True
        )
        GeographicalEntityF.create(
            uuid=str(uuid.uuid4()),
            dataset=self.dataset,
            level=2,
            parent=geo,
            unique_code='GO_001_001',
            is_approved=True,
            is_latest=True
        )
        kwargs = {
            'uuid': self.dataset.uuid,
            'concept_uuid': geo.uuid,
        }
        request = self.factory.get(
            reverse('v1:dataset-entity-hierarchy', kwargs=kwargs)
        )
        request.user = self.superuser
        view = DatasetEntityListHierarchical.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('GO_001_V1', response.data[0])
        self.assertEqual(
            response.data[0]['GO_001_V1'][0], 'GO_001_001_V1')
        self.check_disabled_module(view, request, kwargs=kwargs)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    def test_dataset_export_download(self):
        dataset = DatasetF.create(
            label='test_123',
            uuid=uuid.UUID('e081d207-d0e1-485b-abab-ad29bc7013fe')
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK'
        )
        GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001'
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-download',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetExportDownload.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset.label}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('test_123_all_adm0.geojson', name_list)
                self.assertIn('test_123_all_adm1.geojson', name_list)
        # test update module to inactive
        dataset.module.is_active = False
        dataset.module.save()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)


    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    def test_dataset_export_download_by_level(self):
        dataset = DatasetF.create(
            label='test_123',
            uuid=uuid.UUID('e081d207-d0e1-485b-abab-ad29bc7013fe')
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK'
        )
        GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001'
        )
        kwargs = {
            'uuid': str(dataset.uuid),
            'admin_level': 1
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-download-by-level',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetExportDownloadByLevel.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset.label}_adm1.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertNotIn('test_123_all_adm0.geojson', name_list)
                self.assertIn('test_123_all_adm1.geojson', name_list)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    def test_dataset_export_download_by_country_level(self):
        dataset = DatasetF.create(
            label='test_123',
            uuid=uuid.UUID('e081d207-d0e1-485b-abab-ad29bc7013fe')
        )
        parent = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=parent,
            default=True,
            value='PAK_111'
        )
        GeographicalEntityF.create(
            dataset=dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001'
        )
        kwargs = {
            'uuid': str(dataset.uuid),
            'id_type': self.pCode.name,
            'id': 'PAK_111'
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-download-by-country',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetExportDownloadByCountry.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset.label}_PAK.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('test_123_PAK_adm0.geojson', name_list)
                self.assertIn('test_123_PAK_adm1.geojson', name_list)
        kwargs = {
            'uuid': str(dataset.uuid),
            'id_type': self.pCode.name,
            'id': 'PAK_111',
            'admin_level': 1
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-download-by-country-and-level',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetExportDownloadByCountryAndLevel.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset.label}_PAK_adm1.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertNotIn('test_123_PAK_adm0.geojson', name_list)
                self.assertIn('test_123_PAK_adm1.geojson', name_list)
        # test multiple countries with same ID
        parent2 = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_123'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=parent2,
            default=True,
            value='PAK_111'
        )
        kwargs = {
            'uuid': str(dataset.uuid),
            'id_type': self.pCode.name,
            'id': 'PAK_111'
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-download-by-country',
                kwargs=kwargs
            )
        )
        scheme = versioning.NamespaceVersioning
        view = DatasetExportDownloadByCountry.as_view(
            versioning_class=scheme
        )
        request.resolver_match = FakeResolverMatchV1
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset.label}.zip"'
        )
        with io.BytesIO(response.content) as f:
            with zipfile.ZipFile(f, 'r') as archive:
                self.assertIsNone(archive.testzip())
                name_list = archive.namelist()
                self.assertIn('test_123_PAK_adm0.geojson', name_list)
                self.assertIn('test_123_PAK_adm1.geojson', name_list)
                self.assertIn('test_123_PAK_123_adm0.geojson', name_list)
