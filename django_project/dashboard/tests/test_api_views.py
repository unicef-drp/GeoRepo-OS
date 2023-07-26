import mock
import uuid
import json
from collections import OrderedDict
from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q

from rest_framework.test import APIRequestFactory, APIClient
from core.settings.utils import absolute_path

from dashboard.api_views.boundary_comparison import (
    BoundaryComparisonSummary,
    BoundaryComparisonMatchTable
)
from dashboard.api_views.dataset import (
    DeleteDataset, DatasetEntityList
)
from dashboard.api_views.entity import EntityByConceptUCode
from dashboard.api_views.language import LanguageList, FetchLanguages
from dashboard.api_views.layer_upload import (
    LayerUploadView,
    LayerRemoveView,
    LayersProcessView,
    LayerProcessStatusView,
    UpdateLayerUpload,
    LayerFileEntityTypeList,
    LayerFileChangeLevel,
    LayerFileDownload
)
from dashboard.api_views.layer_config import (
    LayerConfigList,
    LoadLayerConfig,
    SaveLayerConfig
)
from dashboard.api_views.id_type import (
    IdTypeList,
    AddIdType
)
from dashboard.api_views.reviews import (
    ReviewList,
    ApproveRevision, RejectRevision
)
from dashboard.api_views.module import ModuleDashboard
from georepo.models import (
    IdType, GeographicalEntity, Dataset,
    DatasetView, AdminLevelTilingConfig,
    DatasetAdminLevelName, BoundaryType
)
from dashboard.api_views.views import (
    CreateNewView, ViewList, DeleteView, UpdateView, ViewDetail,
    DownloadView
)
from dashboard.models import (
    LayerFile,
    LayerUploadSession,
    PROCESSING,
    LayerConfig,
    PENDING,
    REVIEWING, EntityUploadStatus,
    APPROVED, DONE, REJECTED, ERROR,
    BoundaryComparison
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF, \
    EntityUploadF, BoundaryComparisonF
from georepo.tests.model_factories import (
    UserF, DatasetF, GeographicalEntityF, DatasetViewF, ModuleF,
    LanguageF, DatasetAdminLevelNameF, BoundaryTypeF, EntityTypeF
)
from dashboard.api_views.boundary_comparison import (
    RematchClosestEntities,
    CompareBoundary,
    ConfirmRematchBoundary,
    SwapEntityConcept,
    BoundaryComparisonGeometry
)
from dashboard.api_views.upload_session import (
    CanAddUpload,
    DeleteUploadSession,
    UpdateUploadSession
)
from georepo.utils.tile_configs import populate_tile_configs
from dashboard.api_views.dataset import (
    CheckDatasetShortCode,
    UpdateDataset,
    DatasetAdminLevelNames,
    DatasetBoundaryTypes
)
from georepo.utils.permission import (
    grant_dataset_manager,
    grant_datasetview_owner,
    WRITE_DATASET_PERMISSION_LIST
)
from modules.admin_boundaries.review import approve_revision
from dashboard.api_views.tiling_config import (
    FetchDatasetTilingConfig, UpdateDatasetTilingConfig,
    FetchDatasetViewTilingConfig, UpdateDatasetViewTilingConfig
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest
)
from georepo.utils.dataset_view import (
    init_view_privacy_level
)


def mocked_cache_get(self, *args, **kwargs):
    return OrderedDict()


class DummyRequest:
    @staticmethod
    def json():
        return [
            {
                'name': 'TEST',
                'languages': [
                    {
                        'iso639_1': "en",
                        'iso639_2': "eng",
                        'name': "English",
                        'nativeName': "English"
                    }
                ],
            },
            {
                'name': 'TEST2',
                'languages': [
                    {
                        'iso639_1': "ja",
                        'iso639_2': "jpn",
                        'name': "Japanese",
                        'nativeName': "日本語 (にほんご)"
                    }
                ]
            },
        ]


def mocked_get_language_requests(*args, **kwargs):
    return DummyRequest


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process_layer_upload_session(*args, **kwargs):
    return DummyTask('1')


def mocked_run_comparison_boundary(*args, **kwargs):
    return True


def mocked_run_generate_vector_tiles(*args, **kwargs):
    return DummyTask('1')


def mocked_revoke_running_task(*args, **kwargs):
    return True


class TestApiViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.superuser = UserF.create(is_superuser=True)

    @mock.patch(
        'dashboard.api_views.layer_upload.validate_layer_file_in_crs_4326',
        mock.Mock(return_value=(True, 'EPSG:4326')))
    def test_layer_upload(self):
        file = SimpleUploadedFile(
            'admin.geojson',
            b'file_content',
            content_type='application/geo+json')
        upload_session = LayerUploadSessionF.create()
        request = self.factory.post(
            reverse('layer-upload'), {
                'uploadSession': upload_session.id,
                'id': 'layer-id',
                'file': file
            }
        )
        request.user = UserF.create()
        view = LayerUploadView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(LayerFile.objects.filter(
            name='admin.geojson',
            meta_id='layer-id'
        ).exists())

    def test_layer_process_status(self):
        upload_session = LayerUploadSessionF.create()
        request = self.factory.get(
            reverse('layers-process-status') + (
                f'?session_id={upload_session.id}'
            )
        )
        user = UserF.create(username='test')
        request.user = user
        view = LayerProcessStatusView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)

        request = self.factory.get(
            reverse('layers-process-status')
        )
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 404)

        request = self.factory.get(
            reverse('layers-process-status') + (
                '?session_id=9999'
            )
        )
        request.user = user
        view = LayerProcessStatusView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 404)

    def test_remove_layer(self):
        # test first upload level 0, then remove 0
        upload_session_0 = LayerUploadSessionF.create()
        layer_file_0 = LayerFileF.create(
            layer_upload_session=upload_session_0,
            meta_id='test_0',
            level='0')
        LayerFileF.create(
            layer_upload_session=upload_session_0,
            meta_id='test_0_1',
            level='1')
        request = self.factory.post(
            reverse('layer-remove'), {
                'meta_id': layer_file_0.meta_id,
            }
        )
        request.user = UserF.create(username='test0')
        view = LayerRemoveView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            LayerFile.objects.filter(meta_id=layer_file_0.meta_id).exists())
        # validate test_0_1 have updated levels
        self.assertEqual(
            LayerFile.objects.get(meta_id='test_0_1').level, '0')

        # test upload level 1/2/3, then remove 1
        upload_session = LayerUploadSessionF.create()
        layer_file_1 = LayerFileF.create(
            layer_upload_session=upload_session,
            meta_id='test_1',
            level='1')
        LayerFileF.create(
            layer_upload_session=upload_session,
            meta_id='test_2',
            level='2')
        LayerFileF.create(
            layer_upload_session=upload_session,
            meta_id='test_3',
            level='3')
        request = self.factory.post(
            reverse('layer-remove'), {
                'meta_id': layer_file_1.meta_id,
            }
        )
        request.user = UserF.create(username='test')
        view = LayerRemoveView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            LayerFile.objects.filter(meta_id=layer_file_1.meta_id).exists())
        # validate layer_file_2 and layer_file_3 have updated levels
        self.assertEqual(
            LayerFile.objects.get(meta_id='test_2').level, '1')
        self.assertEqual(
            LayerFile.objects.get(meta_id='test_3').level, '2')

    @mock.patch(
        'dashboard.api_views.layer_upload.process_layer_upload_session.delay',
        mock.Mock(side_effect=mocked_process_layer_upload_session))
    def test_process_layers(self):
        uploader = UserF.create(username='uploader')
        dataset = DatasetF.create()
        layer_file_1 = LayerFileF.create(
            meta_id='test_1',
            uploader=uploader)
        layer_file_2 = LayerFileF.create(meta_id='test_2', uploader=uploader)
        post_data = {
            'entity_types': {
                layer_file_1.meta_id: 'Country',
                layer_file_2.meta_id: 'Region'
            },
            'levels': {
                layer_file_1.meta_id: '0',
                layer_file_2.meta_id: '1'
            },
            'all_files': [
                {
                    'id': layer_file_1.meta_id,
                },
                {
                    'id': layer_file_2.meta_id,
                }
            ],
            'dataset': dataset.label,
            'code_format': 'code_{level}',
            'label_format': 'admin_{level}'
        }
        request = self.factory.post(
            reverse('layers-process'), post_data,
            format='json'
        )
        request.user = UserF.create(username='test')
        view = LayersProcessView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LayerUploadSession.objects.filter(
                dataset=dataset,
                status=PROCESSING
            ).exists()
        )

    def test_layer_config(self):
        created_by = UserF.create(username='test_user')
        # test list config empty
        request = self.factory.get(
            reverse('layer-config-list') + (
                '?level=1'
            )
        )
        request.user = created_by
        list_config_view = LayerConfigList.as_view()
        response = list_config_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        # test save config
        upload_session = LayerUploadSessionF.create()
        post_data = {
            'name': 'Config ABC',
            'level': '1',
            'location_type_field': 'type',
            'parent_id_field': 'code_0',
            'source_field': 'source_id',
            'id_fields': [
                {
                    'id': '1',
                    'field': 'code_1',
                    'idType': {
                        'id': '1',
                        'name': 'PCode'
                    },
                    'default': True
                }
            ],
            'name_fields': [
                {
                    'id': '1',
                    'field': 'name_1',
                    'default': True,
                    'selectedLanguage': 1
                }
            ],
            'layer_upload_session': upload_session.id
        }
        request = self.factory.post(
            reverse('save-layer-config'), post_data,
            format='json'
        )
        request.user = created_by
        save_config_view = SaveLayerConfig.as_view()
        response = save_config_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LayerConfig.objects.filter(
                dataset=upload_session.dataset,
                name='Config ABC'
            ).exists()
        )
        config_id = response.data['id']
        # test load config found
        request = self.factory.get(
            reverse('load-layer-config') + (
                f'?id={config_id}'
            )
        )
        request.user = created_by
        load_config_view = LoadLayerConfig.as_view()
        response = load_config_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Config ABC')
        # test load config not found
        request = self.factory.get(
            reverse('load-layer-config') + (
                '?id=99999'
            )
        )
        request.user = created_by
        response = load_config_view(request)
        self.assertEqual(response.status_code, 404)
        # test list config found 1
        request = self.factory.get(
            reverse('layer-config-list') + (
                '?level=1'
            )
        )
        request.user = created_by
        response = list_config_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Config ABC')

    def test_id_type(self):
        created_by = UserF.create(username='test_user')
        # fetch id list, should return 2 items
        # migration script will insert PCode and Id
        request = self.factory.get(
            reverse('id-type-list')
        )
        request.user = created_by
        id_type_list_view = IdTypeList.as_view()
        response = id_type_list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'PCode')
        self.assertEqual(response.data[0]['id'], 1)
        self.assertEqual(response.data[1]['name'], 'Id')
        self.assertEqual(response.data[1]['id'], 2)
        # add 1 new record, should success
        post_data = {
            'name': 'PCode_1'
        }
        request = self.factory.post(
            reverse('add-id-type'), post_data,
            format='json'
        )
        request.user = created_by
        add_id_type_view = AddIdType.as_view()
        response = add_id_type_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'PCode_1')
        # add same record, should Failed
        request = self.factory.post(
            reverse('add-id-type'), post_data,
            format='json'
        )
        request.user = created_by
        response = add_id_type_view(request)
        self.assertEqual(response.status_code, 400)
        # add 1 new record with trailing spaces, should be trimmed
        post_data = {
            'name': 'PCode-2    '
        }
        request = self.factory.post(
            reverse('add-id-type'), post_data,
            format='json'
        )
        request.user = created_by
        response = add_id_type_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'PCode-2')
        self.assertTrue(IdType.objects.filter(
            name='PCode-2'
        ).exists())
        # add invalid name, should failed
        post_data = {
            'name': '   '
        }
        request = self.factory.post(
            reverse('add-id-type'), post_data,
            format='json'
        )
        request.user = created_by
        add_id_type_view = AddIdType.as_view()
        response = add_id_type_view(request)
        self.assertEqual(response.status_code, 400)
        post_data = {
            'name': 'PCode@2'
        }
        request = self.factory.post(
            reverse('add-id-type'), post_data,
            format='json'
        )
        request.user = created_by
        add_id_type_view = AddIdType.as_view()
        response = add_id_type_view(request)
        self.assertEqual(response.status_code, 400)

    def test_get_review_list(self):
        user = UserF.create(
            username='test_user',
            is_superuser=True, is_staff=True)
        entity = GeographicalEntityF.create()
        upload_session = LayerUploadSessionF.create(
            uploader=user
        )
        EntityUploadF.create(
            status=REVIEWING,
            revised_geographical_entity=entity,
            upload_session=upload_session
        )

        request = self.factory.get(
            reverse('review-list')
        )
        request.user = user
        view = ReviewList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_update_layer_upload(self):
        updated_by = UserF.create(username='test_user')
        upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        layer_file_1 = LayerFileF.create(
            meta_id='test_1',
            uploader=updated_by,
            layer_upload_session=upload_session
        )
        # test using location_type_field
        post_data = {
            'id': layer_file_1.id,
            'location_type_field': 'adm0_id'
        }
        request = self.factory.post(
            reverse('update-layer-upload'),
            post_data,
            format='json'
        )
        request.user = updated_by
        update_layer_view = UpdateLayerUpload.as_view()
        response = update_layer_view(request)
        self.assertEqual(response.status_code, 200)
        layer_file_test_1 = LayerFile.objects.get(
            id=layer_file_1.id
        )
        self.assertEqual(layer_file_test_1.location_type_field, 'adm0_id')
        self.assertEqual(layer_file_test_1.entity_type, '')
        # test using location_type_field
        post_data = {
            'id': layer_file_1.id,
            'entity_type': 'Country'
        }
        request = self.factory.post(
            reverse('update-layer-upload'),
            post_data,
            format='json'
        )
        request.user = updated_by
        response = update_layer_view(request)
        self.assertEqual(response.status_code, 200)
        layer_file_test_1 = LayerFile.objects.get(
            id=layer_file_1.id
        )
        self.assertEqual(layer_file_test_1.location_type_field, '')
        self.assertEqual(layer_file_test_1.entity_type, 'Country')

    @mock.patch(
        'dashboard.api_views.reviews.run_comparison_boundary.apply_async',
        mock.Mock(side_effect=mocked_run_comparison_boundary)
    )
    def test_send_to_ready_reviews(self):
        user = UserF.create(
            username='bob', is_staff=True)
        client = APIClient()
        client.force_login(user)
        dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=False
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=user,
            status='Processing'
        )
        geo = GeographicalEntityF.create(label='test')
        geo_2 = GeographicalEntityF.create(label='test2')
        entity_upload = EntityUploadF.create(
            revised_geographical_entity=geo,
            upload_session=upload_session,
            status='Valid'
        )
        entity_upload_2 = EntityUploadF.create(
            revised_geographical_entity=geo_2,
            upload_session=upload_session,
            status='Valid'
        )
        response = client.post(
            reverse('ready-to-review'),
            {
                'upload_entities': f'{entity_upload.id},{entity_upload_2.id}'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            LayerUploadSession.objects.get(id=upload_session.id).status,
            'Reviewing'
        )
        request = self.factory.get(
            reverse('review-list')
        )
        request.user = self.superuser
        view = ReviewList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['submitted_by'], user.username)
        # simulate when there is other upload in review of same entity
        upload_session_2 = LayerUploadSessionF.create(
            dataset=upload_session.dataset
        )
        geo_ori = GeographicalEntityF.create(
            label='test',
            dataset=upload_session.dataset
        )
        EntityUploadF.create(
            status=REVIEWING,
            original_geographical_entity=geo_ori,
            upload_session=upload_session_2
        )
        entity_upload.original_geographical_entity = geo_ori
        entity_upload.save()
        response = client.post(
            reverse('ready-to-review'),
            {
                'upload_entities': f'{entity_upload.id},{entity_upload_2.id}'
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_get_boundary_comparison_summary(self):
        entity_upload_status = EntityUploadF.create(
            boundary_comparison_summary='test'
        )
        user = UserF.create()
        kwargs = {
            'entity_upload_id': entity_upload_status.id
        }
        request = self.factory.get(
            reverse('boundary-comparison-summary', kwargs=kwargs)
        )
        request.user = user
        view = BoundaryComparisonSummary.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 'test')

        entity_upload_status = EntityUploadF.create(
            boundary_comparison_summary=None,
            comparison_data_ready=None
        )
        kwargs = {
            'entity_upload_id': entity_upload_status.id
        }
        request = self.factory.get(
            reverse('boundary-comparison-summary', kwargs=kwargs)
        )
        request.user = user
        view = BoundaryComparisonSummary.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, None)

    def test_get_boundary_table_data(self):
        # BoundaryComparisonMatchTable
        rev_1_geo_1 = GeographicalEntityF.create(
            revision_number=1,
            level=0
        )
        GeographicalEntityF.create(
            revision_number=1,
            parent=rev_1_geo_1,
            level=1
        )
        rev_2_geo_1 = GeographicalEntityF.create(
            revision_number=1,
            level=0
        )
        rev_2_geo_2 = GeographicalEntityF.create(
            revision_number=1,
            parent=rev_2_geo_1,
            level=1,
            label='test123'
        )
        BoundaryComparisonF.create(
            main_boundary=rev_2_geo_2
        )
        entity_upload = EntityUploadF.create(
            original_geographical_entity=rev_1_geo_1,
            revised_geographical_entity=rev_2_geo_1
        )
        user = UserF.create()
        kwargs = {
            'entity_upload_id': entity_upload.id,
            'level': 1
        }
        request = self.factory.get(
            reverse('boundary-comparison-match-table', kwargs=kwargs)
        )
        request.user = user
        view = BoundaryComparisonMatchTable.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(
            response.data['results'][0]['new_name'],
            rev_2_geo_2.label
        )
        # use filter
        kwargs = {
            'entity_upload_id': entity_upload.id,
            'level': 1
        }
        request = self.factory.get(
            reverse(
                'boundary-comparison-match-table',
                kwargs=kwargs
            ) + '/?search_text=test123'
        )
        request.user = user
        view = BoundaryComparisonMatchTable.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertEqual(
            response.data['results'][0]['new_name'],
            rev_2_geo_2.label
        )

    def test_layer_file_entity_type_list(self):
        request_by = UserF.create(username='test_user')
        request = self.factory.get(
            reverse('layer-entity-type-list')
        )
        request.user = request_by
        view = LayerFileEntityTypeList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        # insert 1 layer with entity_type country
        layer_file_1 = LayerFileF.create(
            meta_id='test_1',
            entity_type='country',
            uploader=request_by)
        view = LayerFileEntityTypeList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn(layer_file_1.entity_type, response.data)

    @mock.patch(
        'modules.admin_boundaries.review.trigger_generate_dynamic_views'
    )
    @mock.patch(
        'dashboard.api_views.reviews.review_approval.delay'
    )
    def test_approve_and_reject_revision(self, mocked_review_app,
                                         mocked_dynamic_views):
        upload_session = LayerUploadSessionF.create(
            status=REVIEWING,
            dataset=self.dataset
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session
        )
        geo_old = GeographicalEntityF.create(
            level=0,
            is_approved=True,
            is_latest=True,
            dataset=upload_session.dataset,
            unique_code='PAK',
            concept_ucode='#PAK_1'
        )
        geo_old_1 = GeographicalEntityF.create(
            level=1,
            is_approved=True,
            is_latest=True,
            parent=geo_old,
            ancestor=geo_old,
            dataset=upload_session.dataset,
            unique_code='PAK_001',
            concept_ucode='#PAK_2'
        )
        geo_old_2 = GeographicalEntityF.create(
            level=2,
            is_approved=True,
            is_latest=True,
            parent=geo_old_1,
            ancestor=geo_old,
            dataset=upload_session.dataset,
            unique_code='PAK_001_001',
            concept_ucode='#PAK_3'
        )
        geo_new = GeographicalEntityF.create(
            level=0,
            is_approved=None,
            is_latest=None,
            dataset=upload_session.dataset,
            unique_code=geo_old.unique_code,
            layer_file=layer_file
        )
        geo_new_1 = GeographicalEntityF.create(
            level=1,
            is_approved=None,
            is_latest=None,
            parent=geo_new,
            ancestor=geo_new,
            dataset=upload_session.dataset,
            unique_code=geo_old_1.unique_code,
            layer_file=layer_file
        )
        geo_new_2 = GeographicalEntityF.create(
            level=2,
            is_approved=None,
            is_latest=None,
            ancestor=geo_new,
            parent=geo_new_1,
            dataset=upload_session.dataset,
            unique_code=geo_old_2.unique_code,
            layer_file=layer_file
        )
        # create boundary comparisons
        BoundaryComparisonF.create(
            main_boundary=geo_new,
            comparison_boundary=geo_old,
            is_same_entity=True
        )
        BoundaryComparisonF.create(
            main_boundary=geo_new_1,
            comparison_boundary=geo_old_1,
            is_same_entity=True
        )
        BoundaryComparisonF.create(
            main_boundary=geo_new_2,
            comparison_boundary=geo_old_2,
            is_same_entity=True
        )

        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_old,
            revised_geographical_entity=geo_new,
            status=REVIEWING
        )
        request_by = UserF.create(
            username='test_user',
            is_staff=True,
            is_superuser=True
        )
        mocked_dynamic_views.side_effect = mocked_run_generate_vector_tiles
        mocked_review_app.side_effect = mocked_run_generate_vector_tiles
        kwargs = {
            'uuid': str(upload_session.dataset.uuid)
        }
        request = self.factory.post(
            reverse('approve-revision', kwargs=kwargs),
            {
                'entity_upload_id': entity_upload.id
            }
        )
        request.user = request_by
        view = ApproveRevision.as_view()
        response = view(request, **kwargs)
        approve_revision(entity_upload, request_by)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            EntityUploadStatus.objects.get(
                id=entity_upload.id
            ).status, APPROVED
        )
        self.assertEqual(
            LayerUploadSession.objects.get(
                id=upload_session.id
            ).status, DONE
        )
        self.assertTrue(
            GeographicalEntity.objects.filter(
                id__in=geo_new.all_children(),
                is_approved=True,
                is_latest=True
            ),
            3
        )
        updated_geo_old = GeographicalEntity.objects.get(id=geo_old.id)
        self.assertFalse(updated_geo_old.is_latest)
        self.assertEqual(updated_geo_old.end_date, upload_session.started_at)
        # ensure default views are generated
        self.assertEqual(
            DatasetView.objects.filter(
                dataset=upload_session.dataset
            ).count(),
            4
        )
        # check dynamic views have been refreshed
        mocked_dynamic_views.assert_called_once_with(
            self.dataset,
            adm0=geo_new
        )
        # check concept ucode have been generated
        self.assertFalse(
            GeographicalEntity.objects.filter(
                id__in=geo_new.all_children(),
            ).filter(
                Q(concept_ucode__isnull=True) | Q(concept_ucode='')
            ).exists()
        )

        request = self.factory.post(
            reverse('reject-revision', kwargs=kwargs),
            {
                'entity_upload_id': entity_upload.id
            }
        )
        request.user = request_by
        view = RejectRevision.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        updated_upload = EntityUploadStatus.objects.get(
            id=entity_upload.id
        )
        self.assertEqual(
            updated_upload.status, REJECTED
        )
        self.assertFalse(updated_upload.revised_entity_id)
        self.assertEqual(
            geo_new.all_children().count(),
            0
        )

    def test_layer_file_change_level(self):
        uploader = UserF.create(username='uploader')
        layer_file_1 = LayerFileF.create(
            meta_id='test_1',
            level='1',
            uploader=uploader)
        layer_file_2 = LayerFileF.create(
            meta_id='test_2',
            level='2',
            uploader=uploader)
        post_data = {
            'levels': {
                layer_file_1.meta_id: '2',
                layer_file_2.meta_id: '1'
            }
        }
        request = self.factory.post(
            reverse('layer-file-change-level'), post_data,
            format='json'
        )
        request.user = uploader
        layer_change_level = LayerFileChangeLevel.as_view()
        response = layer_change_level(request)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            LayerFile.objects.get(id=layer_file_1.id).level,
            '2'
        )
        self.assertEqual(
            LayerFile.objects.get(id=layer_file_2.id).level,
            '1'
        )

    @mock.patch(
        'dashboard.api_views.views.trigger_generate_vector_tile_for_view',
        mock.Mock(side_effect=mocked_process_layer_upload_session))
    def test_create_new_view(self):
        user = UserF.create(username='creator')
        dataset = DatasetF.create()
        post_data = {
            'name': 'test',
            'dataset_id': dataset.id
        }
        request = self.factory.post(
            reverse('create-new-view'), post_data,
            format='json'
        )
        request.user = user
        create_new_view = CreateNewView.as_view()
        response = create_new_view(request)
        self.assertEqual(response.status_code, 404)

        post_data = {
            'name': 'test',
            'dataset_id': dataset.id,
            'description': 'desc',
            'mode': 'static',
            'query_string': 'DROP TABLE geographicalentity'
        }
        request = self.factory.post(
            reverse('create-new-view'), post_data,
            format='json'
        )
        request.user = user
        response = create_new_view(request)
        self.assertEqual(response.status_code, 404)

        post_data = {
            'name': 'test',
            'dataset_id': dataset.id,
            'description': 'desc',
            'mode': 'static',
            'tags': ['test', 'test2'],
            'query_string': (
                'select * from georepo_geographicalentity '
            )
        }
        request = self.factory.post(
            reverse('create-new-view'), post_data,
            format='json'
        )
        request.user = user
        response = create_new_view(request)
        self.assertEqual(response.status_code, 201)

        filter_data = post_data
        del filter_data['mode']
        del filter_data['tags']
        del filter_data['query_string']
        filter_data['is_static'] = True
        filter_data['tags__name'] = 'test'
        self.assertTrue(
            DatasetView.objects.filter(
                **filter_data
            ).exists()
        )

    def test_delete_dataset(self):
        # Test no permission
        user = UserF.create()
        dataset = DatasetF.create()
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset.id
        })
        self.assertEqual(response.status_code, 403)

        # Test creator deleting dataset
        dataset_1 = DatasetF.create(created_by=user)
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset_1.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset_1.id
        })
        self.assertEqual(response.status_code, 200)

        # Test superuser deleting dataset
        superuser = UserF.create(is_superuser=True)
        dataset_2 = DatasetF.create(created_by=superuser)
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset_2.id
            }), {},
            format='json'
        )
        request.user = superuser
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset_2.id
        })
        self.assertEqual(response.status_code, 200)

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_get_dataset_entity_list_by_session(self):
        from dashboard.tests.model_factories import LayerUploadSessionF,\
            LayerFileF
        from dashboard.tasks import layer_upload_preprocessing
        uuid_code = str(uuid.uuid4())
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        language = LanguageF.create()
        LayerFileF.create(
            layer_upload_session=upload_session,
            level='0',
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
            layer_file=(
                absolute_path('dashboard', 'tests',
                              'geojson_dataset', 'level_0_3.geojson')
            )
        )
        entity1 = GeographicalEntityF.create(
            level=0,
            uuid=uuid_code,
            dataset=upload_session.dataset,
            is_latest=True,
            is_approved=True,
            label='Test',
            internal_code='Test-01',
            revision_number=1
        )
        layer_upload_preprocessing(upload_session.id)
        request = self.factory.get(
            reverse('dataset-entity-list') + f'?session={upload_session.id}'
        )
        request.user = UserF.create()
        view = DatasetEntityList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['layer0_id'], 'PAK')
        self.assertFalse(response.data['results'][0]['country_entity_id'])
        self.assertTrue(response.data['results'][0]['is_selected'])
        self.assertTrue(response.data['results'][0]['is_available'])
        self.assertEqual(response.data['results'][1]['layer0_id'], 'IND')
        self.assertFalse(response.data['results'][1]['country_entity_id'])
        self.assertTrue(response.data['results'][1]['is_selected'])
        self.assertTrue(response.data['results'][1]['is_available'])
        # change existing entity to match layer_file0
        entity1.label = 'Test'
        entity1.internal_code = 'PAK'
        entity1.save()
        layer_upload_preprocessing(upload_session.id)
        request = self.factory.get(
            reverse('dataset-entity-list') + f'?session={upload_session.id}'
        )
        request.user = UserF.create()
        view = DatasetEntityList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['layer0_id'], 'PAK')
        self.assertEqual(
            response.data['results'][0]['country_entity_id'],
            entity1.id)
        self.assertTrue(response.data['results'][0]['is_selected'])
        self.assertTrue(response.data['results'][0]['is_available'])
        self.assertTrue(response.data['results'][0]['upload_id'])
        self.assertEqual(response.data['results'][1]['layer0_id'], 'IND')
        self.assertFalse(response.data['results'][1]['country_entity_id'])
        self.assertTrue(response.data['results'][1]['is_selected'])
        self.assertTrue(response.data['results'][1]['is_available'])
        self.assertTrue(response.data['results'][1]['upload_id'])
        # simulate fetch after selection one of the country
        upload_1 = EntityUploadStatus.objects.get(
            id=response.data['results'][0]['upload_id']
        )
        upload_1.max_level = '0'
        upload_1.status = ERROR
        upload_1.revised_geographical_entity = entity1
        upload_1.save()
        request = self.factory.get(
            reverse('dataset-entity-list') + f'?session={upload_session.id}'
        )
        request.user = UserF.create()
        view = DatasetEntityList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['layer0_id'], 'PAK')
        self.assertEqual(
            response.data['results'][0]['country_entity_id'],
            entity1.id)
        self.assertTrue(response.data['results'][0]['is_selected'])
        self.assertTrue(response.data['results'][0]['is_available'])
        self.assertTrue(response.data['results'][0]['upload_id'])
        self.assertEqual(response.data['results'][1]['layer0_id'], 'IND')
        self.assertFalse(response.data['results'][1]['country_entity_id'])
        self.assertFalse(response.data['results'][1]['is_selected'])
        self.assertTrue(response.data['results'][1]['is_available'])
        self.assertTrue(response.data['results'][1]['upload_id'])
        # simulate the entity is used in other session
        upload_1.max_level = ''
        upload_1.status = ''
        upload_1.revised_geographical_entity = None
        upload_1.save()
        upload_session_2 = LayerUploadSessionF.create(
            dataset=upload_session.dataset
        )
        EntityUploadF.create(
            status=REVIEWING,
            original_geographical_entity=entity1,
            upload_session=upload_session_2
        )
        request = self.factory.get(
            reverse('dataset-entity-list') + f'?session={upload_session.id}'
        )
        request.user = UserF.create()
        view = DatasetEntityList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['layer0_id'], 'PAK')
        self.assertEqual(
            response.data['results'][0]['country_entity_id'],
            entity1.id)
        self.assertTrue(response.data['results'][0]['is_selected'])
        self.assertFalse(response.data['results'][0]['is_available'])
        self.assertTrue(response.data['results'][0]['upload_id'])
        self.assertEqual(response.data['results'][1]['layer0_id'], 'IND')
        self.assertFalse(response.data['results'][1]['country_entity_id'])
        self.assertTrue(response.data['results'][1]['is_selected'])
        self.assertTrue(response.data['results'][1]['is_available'])
        self.assertTrue(response.data['results'][1]['upload_id'])

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_get_dataset_entity_list_read_only(self):
        from dashboard.tests.model_factories import LayerUploadSessionF,\
            LayerFileF
        from dashboard.tasks import layer_upload_preprocessing
        uuid_code = str(uuid.uuid4())
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            status=DONE
        )
        language = LanguageF.create()
        LayerFileF.create(
            layer_upload_session=upload_session,
            level='0',
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
            layer_file=(
                absolute_path('dashboard', 'tests',
                              'geojson_dataset', 'level_0_3.geojson')
            )
        )
        entity1 = GeographicalEntityF.create(
            level=0,
            uuid=uuid_code,
            dataset=upload_session.dataset,
            is_latest=True,
            is_approved=True,
            label='Test',
            internal_code='Test-01',
            revision_number=1
        )
        layer_upload_preprocessing(upload_session.id)
        upload_1 = (
            upload_session.entityuploadstatus_set.filter(
                revised_entity_id='PAK'
            ).first()
        )
        upload_1.max_level = '0'
        upload_1.status = ERROR
        upload_1.revised_geographical_entity = entity1
        upload_1.save()
        request = self.factory.get(
            reverse('dataset-entity-list') + f'?session={upload_session.id}'
        )
        request.user = UserF.create()
        view = DatasetEntityList.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['layer0_id'], 'PAK')
        self.assertFalse(response.data['results'][0]['country_entity_id'])
        self.assertTrue(response.data['results'][0]['is_selected'])
        self.assertTrue(response.data['results'][0]['is_available'])
        self.assertEqual(response.data['results'][1]['layer0_id'], 'IND')
        self.assertFalse(response.data['results'][1]['country_entity_id'])
        self.assertFalse(response.data['results'][1]['is_selected'])
        self.assertTrue(response.data['results'][1]['is_available'])

    def test_get_module_list(self):
        ModuleF.create()
        request = self.factory.get(
            reverse('module-list')
        )
        request.user = self.superuser
        view = ModuleDashboard.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) > 0)

    def test_create_dataset(self):
        module = ModuleF.create()
        user = UserF.create(
            username='test', is_superuser=True, is_staff=True)
        client = APIClient()
        client.force_login(user=user)
        response = client.post(
            reverse('create-dataset'),
            {
                'module_id': module.id,
                'name': 'test_dataset',
                'description': 'dataset_desc',
                'short_code': 'OAB1'
            }
        )
        self.assertEqual(response.status_code, 201)
        dataset = Dataset.objects.filter(label='test_dataset')
        self.assertTrue(
            dataset.exists()
        )
        self.assertEqual(
            DatasetAdminLevelName.objects.filter(
                dataset=dataset.first()
            ).count(),
            4
        )
        self.assertTrue(
            Dataset.objects.filter(short_code='OAB1').exists()
        )
        # create duplicate short_code should return 400
        response = client.post(
            reverse('create-dataset'),
            {
                'module_id': module.id,
                'name': 'test_dataset',
                'description': 'dataset_desc',
                'short_code': 'OAB1'
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_list_views(self):
        creator = UserF.create()
        dataset_1 = DatasetViewF.create(
            created_by=creator
        )
        grant_dataset_manager(dataset_1.dataset, creator)
        request = self.factory.get(
            reverse('view-list')
        )
        request.user = self.superuser
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0].get('id'), dataset_1.id)

        request = self.factory.get(
            reverse('view-list')
        )

        request.user = creator
        list_view = ViewList.as_view()
        response = list_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0].get('id'), dataset_1.id)

    def test_delete_view(self):
        # Test no permission
        user = UserF.create()
        view = DatasetViewF.create()
        request = self.factory.post(
            reverse('delete-view', kwargs={
                'id': view.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteView.as_view()
        response = delete_dataset_view(request, **{
            'id': view.id
        })
        self.assertEqual(response.status_code, 403)

        # Test creator deleting dataset
        view_1 = DatasetViewF.create(created_by=user)
        grant_dataset_manager(view_1.dataset, user)
        grant_datasetview_owner(view_1, user)
        request = self.factory.post(
            reverse('delete-view', kwargs={
                'id': view_1.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteView.as_view()
        response = delete_dataset_view(request, **{
            'id': view_1.id
        })
        self.assertEqual(response.status_code, 200)

        # Test superuser deleting dataset
        superuser = UserF.create(is_superuser=True)
        view_2 = DatasetViewF.create(created_by=superuser)
        request = self.factory.post(
            reverse('delete-view', kwargs={
                'id': view_2.id
            }), {},
            format='json'
        )
        request.user = superuser
        delete_dataset_view = DeleteView.as_view()
        response = delete_dataset_view(request, **{
            'id': view_2.id
        })
        self.assertEqual(response.status_code, 200)

    @mock.patch(
        'dashboard.api_views.views.trigger_generate_vector_tile_for_view',
        mock.Mock(side_effect=mocked_process_layer_upload_session))
    @mock.patch(
        'dashboard.api_views.views.simplify_geometry_in_view.delay',
        mock.Mock(side_effect=mocked_process_layer_upload_session))
    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_update_view(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        view_1 = DatasetViewF.create(created_by=user)
        query_string = 'SELECT * from geographicalentity;'
        request = self.factory.post(
            reverse('update-view', kwargs={
                'id': view_1.id
            }), {
                'name': 'update',
                'dataset_id': dataset.id,
                'tags': ['test', 'test2'],
                'query_string': query_string
            },
            format='json'
        )
        request.user = user
        update_dataset_view = UpdateView.as_view()
        response = update_dataset_view(request, **{
            'id': view_1.id
        })
        self.assertEqual(response.status_code, 200)
        dataset_view = DatasetView.objects.get(id=view_1.id)
        self.assertEqual(dataset_view.name, 'update')
        self.assertTrue(dataset_view.tags.all().filter(name='test').exists())

    def test_detail_view(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetViewF.create(
            is_static=False,
        )
        request = self.factory.get(
            reverse('view-detail', kwargs={
                'id': dataset.id
            })
        )
        request.user = user
        detail_view = ViewDetail.as_view()
        response = detail_view(request, **{
            'id': dataset.id
        })
        self.assertEqual(response.status_code, 200)

    def test_get_closest_entities(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        parent = GeographicalEntityF.create(
            level=0,
            dataset=dataset,
            is_latest=True,
            is_approved=True,
            label='Test',
            internal_code='Test-01',
            revision_number=1,
            unique_code='PARENT_0'
        )
        entity_1_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        entity_2_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_2.geojson')
        entity_3_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_3.geojson')
        entity_geojson = [
            entity_1_geojson,
            entity_2_geojson,
            entity_3_geojson
        ]
        index = 0
        geographical_entities = []
        for entity_geojson_path in entity_geojson:
            with open(entity_geojson_path) as geojson:
                data = json.load(geojson)
                geom_str = json.dumps(data['features'][0]['geometry'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=f'CODE_{index}',
                    unique_code=f'CODE_{index}',
                    revision_number=1,
                    parent=parent,
                    ancestor=parent,
                    level=1
                ))
            index += 1
        geographical_entities[0].revision_number = 2
        geographical_entities[0].is_approved = False
        geographical_entities[0].is_latest = False
        geographical_entities[0].save()
        boundary_comparison = BoundaryComparisonF.create(
            main_boundary=geographical_entities[0]
        )
        request = self.factory.get(
            reverse('boundary-comparison-closest', kwargs={
                'boundary_comparison_id': boundary_comparison.id
            })
        )
        request.user = user
        view = RematchClosestEntities.as_view()
        response = view(request, **{
            'boundary_comparison_id': boundary_comparison.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)

    def test_compare_boundary(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        entity_1_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        entity_2_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_2.geojson')
        entity_geojson = [
            entity_1_geojson,
            entity_2_geojson
        ]
        parent = GeographicalEntityF.create(
            level=0,
            dataset=dataset,
            is_latest=True,
            is_approved=True,
            label='Test',
            internal_code='Test-01',
            revision_number=1,
            unique_code='CODE',
            unique_code_version=1
        )
        upload_session = LayerUploadSessionF.create(
            uploader=user
        )
        upload_status = EntityUploadF.create(
            status=REVIEWING,
            revised_geographical_entity=parent,
            upload_session=upload_session
        )
        index = 0
        geographical_entities = []
        for entity_geojson_path in entity_geojson:
            with open(entity_geojson_path) as geojson:
                data = json.load(geojson)
                geom_str = json.dumps(data['features'][0]['geometry'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code='CODE_1',
                    unique_code='CODE_1',
                    unique_code_version=1,
                    revision_number=1,
                    level=1,
                    parent=parent,
                    ancestor=parent
                ))
            index += 1
        # geographical_entities[1] is 2nd revision
        geographical_entities[1].revision_number = 2
        geographical_entities[1].unique_code = 'CODE_2'
        geographical_entities[1].unique_code_version = 2
        geographical_entities[1].is_approved = False
        geographical_entities[1].is_latest = False
        geographical_entities[1].save()
        boundary_comparison = BoundaryComparisonF.create(
            main_boundary=geographical_entities[1]
        )
        kwargs = {
            'entity_upload_id': upload_status.id,
            'boundary_comparison_id': boundary_comparison.id,
            'source_id': geographical_entities[1].id
        }
        request = self.factory.get(
            reverse('boundary-compare-entities', kwargs=kwargs)
        )
        request.user = user
        view = CompareBoundary.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # confirm rematch
        kwargs = {
            'boundary_comparison_id': boundary_comparison.id
        }
        post_data = {
            'source_id': geographical_entities[0].id,
            'entity_upload_id': upload_status.id
        }
        request = self.factory.post(
            reverse('boundary-comparison-rematch', kwargs=kwargs), post_data,
            format='json'
        )
        request.user = user
        view = ConfirmRematchBoundary.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        # assert the concept uuid
        updated_boundary = BoundaryComparison.objects.get(
            id=boundary_comparison.id
        )
        self.assertFalse(updated_boundary.is_same_entity)
        updated_main = GeographicalEntity.objects.get(
            id=boundary_comparison.main_boundary.id
        )
        self.assertNotEqual(updated_main.uuid,
                            updated_boundary.comparison_boundary.uuid)
        # if not same entity, then ensure the unique code is new one
        self.assertNotEqual(updated_main.unique_code,
                            updated_boundary.comparison_boundary.unique_code)
        self.assertFalse(GeographicalEntity.objects.filter(
            dataset=updated_main.dataset,
            level=updated_main.level,
            unique_code_version=2,
            unique_code=updated_main.unique_code
        ).exclude(id=updated_main.id).exists())
        # rematch new entity to same entity
        with open(entity_1_geojson) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            main_entity_1 = GeographicalEntityF.create(
                dataset=dataset,
                is_validated=True,
                is_approved=False,
                is_latest=False,
                geometry=GEOSGeometry(geom_str),
                internal_code='CODE_3',
                unique_code='CODE_3',
                unique_code_version=2,
                revision_number=2,
                level=1,
                parent=parent,
                ancestor=parent
            )
        # creat next entity code CODE_4 and CODE_5
        entity_code_4 = GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=False,
            is_latest=False,
            geometry=GEOSGeometry(geom_str),
            internal_code='CODE_4',
            unique_code='CODE_4',
            unique_code_version=2,
            revision_number=2,
            level=1,
            parent=parent,
            ancestor=parent
        )
        entity_code_5 = GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=False,
            is_latest=False,
            geometry=GEOSGeometry(geom_str),
            internal_code='CODE_5',
            unique_code='CODE_5',
            unique_code_version=2,
            revision_number=2,
            level=1,
            parent=parent,
            ancestor=parent
        )
        boundary_comparison = BoundaryComparisonF.create(
            main_boundary=main_entity_1,
            comparison_boundary=geographical_entities[1],
            is_same_entity=False
        )
        kwargs = {
            'boundary_comparison_id': boundary_comparison.id
        }
        post_data = {
            'source_id': geographical_entities[0].id,
            'entity_upload_id': upload_status.id
        }
        request = self.factory.post(
            reverse('boundary-comparison-rematch', kwargs=kwargs), post_data,
            format='json'
        )
        request.user = user
        view = ConfirmRematchBoundary.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        # assert the concept uuid
        updated_boundary = BoundaryComparison.objects.get(
            id=boundary_comparison.id
        )
        self.assertTrue(updated_boundary.is_same_entity)
        updated_main = GeographicalEntity.objects.get(
            id=boundary_comparison.main_boundary.id
        )
        self.assertEqual(updated_main.uuid,
                         updated_boundary.comparison_boundary.uuid)
        # if same entity, then ensure the unique code is the same
        self.assertEqual(updated_main.unique_code,
                         updated_boundary.comparison_boundary.unique_code)
        self.assertEqual(updated_main.unique_code,
                         'CODE_1')
        updated_code_4 = GeographicalEntity.objects.get(
            id=entity_code_4.id
        )
        self.assertEqual(updated_code_4.unique_code, 'CODE_3')
        updated_code_5 = GeographicalEntity.objects.get(
            id=entity_code_5.id
        )
        self.assertEqual(updated_code_5.unique_code, 'CODE_4')
        self.assertFalse(GeographicalEntity.objects.filter(
            dataset=dataset,
            unique_code_version=2,
            unique_code='CODE_5'
        ).exists())

    def test_can_upload(self):
        dataset = DatasetF.create()
        user_1 = UserF.create()
        grant_dataset_manager(dataset, user_1, WRITE_DATASET_PERMISSION_LIST)
        user_2 = UserF.create()
        grant_dataset_manager(dataset, user_2, WRITE_DATASET_PERMISSION_LIST)
        entity = GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK',
            unique_code='PAK',
            revision_number=1,
            level=0
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=user_1
        )
        kwargs = {
            'id': dataset.id
        }
        request = self.factory.get(
            reverse('can-add-upload', kwargs=kwargs)
        )
        request.user = user_1
        query_view = CanAddUpload.as_view()
        # canUpload = True
        upload_session.status = DONE
        upload_session.save()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['can_upload'])
        # canUpload = False, because REVIEWING UPLOAD
        upload_session.status = PENDING
        upload_session.save()
        EntityUploadF.create(
            status=REVIEWING,
            original_geographical_entity=entity,
            upload_session=upload_session
        )
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_upload'])
        self.assertEqual(
            response.data['active_upload']['id'],
            upload_session.id)
        # canUpload = False, other user should not see user_1 uploads
        request.user = user_2
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_upload'])
        self.assertNotIn('active_upload', response.data)
        # canUpload = True, if there is available country
        GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='AO',
            unique_code='AO',
            revision_number=1,
            level=0
        )
        request.user = user_1
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['can_upload'])
        self.assertIn('active_upload', response.data)
        self.assertEqual(
            response.data['active_upload']['id'],
            upload_session.id
        )
        # block if there is ongoing level 0 upload
        upload_session_2 = LayerUploadSessionF.create(
            dataset=dataset,
            status=PENDING,
            uploader=user_2
        )
        EntityUploadF.create(
            status=PENDING,
            revised_entity_id='SYR',
            original_geographical_entity=None,
            upload_session=upload_session_2
        )
        request.user = user_1
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['can_upload'])
        self.assertNotIn('active_upload', response.data)

    def test_delete_upload_session(self):
        dataset = DatasetF.create()
        user_1 = UserF.create()
        user_2 = UserF.create()
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=user_1
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            uploader=user_1
        )
        entity = GeographicalEntityF.create(
            dataset=dataset,
            layer_file=layer_file
        )
        kwargs = {
            'id': upload_session.id
        }
        request = self.factory.post(
            reverse('delete-upload-session', kwargs=kwargs), {},
            format='json'
        )
        # not permitted
        request.user = user_2
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # status cannot be deleted
        upload_session.status = DONE
        upload_session.save()
        request.user = user_1
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        # can delete, and the entity is deleted too
        upload_session.status = PENDING
        upload_session.save()
        request.user = user_1
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LayerFile.objects.filter(
            id=layer_file.id
        ).exists())
        self.assertFalse(GeographicalEntity.objects.filter(
            id=entity.id
        ).exists())

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_download_layer_file(self):
        # test first upload level 0, then remove 0
        upload_session_0 = LayerUploadSessionF.create()
        layer_file_0 = LayerFileF.create(
            layer_upload_session=upload_session_0,
            meta_id='test_0',
            level='0',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_0.geojson')
            )
        )
        request = self.factory.get(
            reverse('layer-file-download') +
            f'?meta_id={layer_file_0.meta_id}'
        )
        # download as another user, should return no permission
        test0_user = UserF.create(username='test0')
        request.user = test0_user
        view = LayerFileDownload.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 403)
        request = self.factory.get(
            reverse('layer-file-download') +
            f'?meta_id={layer_file_0.meta_id}'
        )
        # download not exists
        request = self.factory.get(
            reverse('layer-file-download') +
            f'?meta_id={layer_file_0.meta_id}_123'
        )
        request.user = upload_session_0.uploader
        view = LayerFileDownload.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 404)
        # download exists
        request = self.factory.get(
            reverse('layer-file-download') +
            f'?meta_id={layer_file_0.meta_id}'
        )
        request.user = upload_session_0.uploader
        view = LayerFileDownload.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Type'))
        self.assertTrue(response.has_header('Content-Disposition'))

    def test_update_upload_session(self):
        user_1 = UserF.create()
        upload_session_0 = LayerUploadSessionF.create()
        post_data = {
            'session': upload_session_0.id,
            'source': 'ABC',
            'description': 'abc'
        }
        request = self.factory.post(
            reverse('update-upload-session'), post_data,
            format='json'
        )
        request.user = user_1
        view = UpdateUploadSession.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        updated = LayerUploadSession.objects.get(id=upload_session_0.id)
        self.assertEqual(updated.source, post_data['source'])
        self.assertFalse(updated.is_historical_upload)
        upload_session_1 = LayerUploadSessionF.create()
        post_data = {
            'session': upload_session_1.id,
            'source': 'ABC',
            'description': 'abc',
            'is_historical_upload': True,
            'historical_start_date': '2022-08-10 14:20:37.131 +0700',
            'historical_end_date': '2022-08-10 14:20:37.131 +0700'
        }
        request = self.factory.post(
            reverse('update-upload-session'), post_data,
            format='json'
        )
        request.user = user_1
        view = UpdateUploadSession.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        updated = LayerUploadSession.objects.get(id=upload_session_1.id)
        self.assertEqual(updated.source, post_data['source'])
        self.assertTrue(updated.is_historical_upload)

    def test_swap_entity_concept(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        entity_1_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        entity_2_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_2.geojson')
        entity_geojson = [
            entity_1_geojson,
            entity_2_geojson
        ]
        index = 0
        geographical_entities = []
        for entity_geojson_path in entity_geojson:
            with open(entity_geojson_path) as geojson:
                data = json.load(geojson)
                geom_str = json.dumps(data['features'][0]['geometry'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=f'CODE_{index}',
                    unique_code=f'CODE_{index}',
                    revision_number=1
                ))
            index += 1
        boundary_comparison = BoundaryComparisonF.create(
            main_boundary=geographical_entities[0],
            comparison_boundary=geographical_entities[1],
            is_same_entity=True
        )
        post_data = {
            'boundary_comparison_id': boundary_comparison.id
        }
        request = self.factory.post(
            reverse('boundary-swap-entity-concept'), post_data,
            format='json'
        )
        request.user = user
        view = SwapEntityConcept.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 204)
        updated = BoundaryComparison.objects.get(
            id=boundary_comparison.id
        )
        self.assertFalse(updated.is_same_entity)
        self.assertNotEqual(
            updated.main_boundary.uuid,
            geographical_entities[1].uuid
        )
        request = self.factory.post(
            reverse('boundary-swap-entity-concept'), post_data,
            format='json'
        )
        request.user = user
        view = SwapEntityConcept.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 204)
        updated = BoundaryComparison.objects.get(
            id=boundary_comparison.id
        )
        self.assertTrue(updated.is_same_entity)
        self.assertEqual(
            updated.main_boundary.uuid,
            geographical_entities[1].uuid
        )

    def test_boundary_comparison_geometry(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create()
        entity_1_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_1.geojson')
        entity_2_geojson = absolute_path(
            'dashboard', 'tests',
            'admin_boundary_matching_data',
            'entity_2.geojson')
        entity_geojson = [
            entity_1_geojson,
            entity_2_geojson
        ]
        index = 0
        geographical_entities = []
        for entity_geojson_path in entity_geojson:
            with open(entity_geojson_path) as geojson:
                data = json.load(geojson)
                geom_str = json.dumps(data['features'][0]['geometry'])
                geographical_entities.append(GeographicalEntityF.create(
                    dataset=dataset,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=GEOSGeometry(geom_str),
                    internal_code=f'CODE_{index}',
                    unique_code=f'CODE_{index}',
                    revision_number=1
                ))
            index += 1
        boundary_comparison = BoundaryComparisonF.create(
            main_boundary=geographical_entities[0],
            comparison_boundary=geographical_entities[1]
        )
        kwargs = {
            'boundary_comparison_id': boundary_comparison.id
        }
        request = self.factory.get(
            reverse('boundary-comparison-geometry', kwargs=kwargs)
        )
        request.user = user
        view = BoundaryComparisonGeometry.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('bbox', response.data)
        self.assertIn('main_boundary_geom', response.data)
        self.assertIn('main_boundary_data', response.data)
        self.assertIn('comparison_boundary_geom', response.data)
        self.assertIn('comparison_boundary_data', response.data)

    def test_check_dataset_short_code(self):
        user = UserF.create(is_superuser=True)
        module = ModuleF.create()
        dataset = DatasetF.create(
            label='Dataset World',
            module=module,
            short_code='ABC1'
        )
        post_data = {
            'short_code': dataset.short_code
        }
        request = self.factory.post(
            reverse('check-dataset-short-code'), post_data, format='json'
        )
        request.user = user
        view = CheckDatasetShortCode.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_available'])
        # new name
        post_data = {
            'short_code': 'ABD1'
        }
        request = self.factory.post(
            reverse('check-dataset-short-code'), post_data, format='json'
        )
        request.user = user
        view = CheckDatasetShortCode.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_available'])
        # exclude the uuid
        post_data = {
            'short_code': dataset.short_code,
            'dataset': str(dataset.uuid)
        }
        request = self.factory.post(
            reverse('check-dataset-short-code'), post_data, format='json'
        )
        request.user = user
        view = CheckDatasetShortCode.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_available'])
        # check more than 4 chars
        post_data = {
            'short_code': 'ABDCE'
        }
        request = self.factory.post(
            reverse('check-dataset-short-code'), post_data, format='json'
        )
        request.user = user
        view = CheckDatasetShortCode.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_available'])

    @mock.patch(
        'modules.admin_boundaries.config.'
        'trigger_generate_vector_tile_for_view'
    )
    def test_update_dataset(self, mocked_view: mock.MagicMock):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create(
            label='Dataset World',
            module=self.module
        )
        # create 1 entity adm0
        adm0 = GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='AO',
            unique_code='AO',
            unique_code_version=1,
            revision_number=1,
            level=0,
            admin_level_name='Country'
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        post_data = {
            'geometry_similarity_threshold_new': 0.4,
            'geometry_similarity_threshold_old': 0.5,
            'generate_adm0_default_views': True,
            'is_active': True
        }
        request = self.factory.post(
            reverse('update-dataset', kwargs=kwargs),
            post_data,
            format='json'
        )
        request.user = user
        view = UpdateDataset.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        updated = Dataset.objects.get(id=dataset.id)
        self.assertEqual(
            updated.geometry_similarity_threshold_new,
            post_data['geometry_similarity_threshold_new']
        )
        self.assertEqual(
            updated.geometry_similarity_threshold_old,
            post_data['geometry_similarity_threshold_old']
        )
        self.assertEqual(updated.label, dataset.label)
        self.assertTrue(updated.generate_adm0_default_views)
        # assert that 2 default views for adm0 are generated
        self.assertEqual(
            DatasetView.objects.filter(
                dataset=dataset,
                default_ancestor_code=adm0.unique_code
            ).exclude(default_type__isnull=True).count(),
            2
        )
        self.assertEqual(mocked_view.call_count, 2)
        mocked_view.reset_mock()
        post_data = {
            'name': 'New World',
            'geometry_similarity_threshold_new': 0.4,
            'geometry_similarity_threshold_old': 0.5,
            'generate_adm0_default_views': False,
            'is_active': True
        }
        request = self.factory.post(
            reverse('update-dataset', kwargs=kwargs),
            post_data,
            format='json'
        )
        request.user = user
        view = UpdateDataset.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        updated = Dataset.objects.get(id=dataset.id)
        self.assertEqual(
            updated.geometry_similarity_threshold_new,
            post_data['geometry_similarity_threshold_new']
        )
        self.assertEqual(
            updated.geometry_similarity_threshold_old,
            post_data['geometry_similarity_threshold_old']
        )
        self.assertEqual(updated.label, post_data['name'])
        self.assertFalse(updated.generate_adm0_default_views)
        self.assertEqual(mocked_view.call_count, 0)
        # setting to false will not remove the views
        self.assertEqual(
            DatasetView.objects.filter(
                dataset=dataset,
                default_ancestor_code=adm0.unique_code
            ).exclude(default_type__isnull=True).count(),
            2
        )

    def test_get_language_list(self):
        user = UserF.create(is_superuser=True)
        LanguageF.create(name='TEST', code='TE', order=1)
        LanguageF.create(name='TEST2', code='TE2', order=2)
        LanguageF.create(name='B', code='B', order=None)
        LanguageF.create(name='A', code='A', order=None)
        view = LanguageList.as_view()
        request = self.factory.get(
            reverse('language-list')
        )
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data[0]['name'], 'TEST')
        self.assertEqual(data[2]['name'], 'A')

    @mock.patch(
        'requests.get',
        mock.Mock(side_effect=mocked_get_language_requests))
    def test_fetch_languages(self):
        user = UserF.create()
        view = FetchLanguages.as_view()
        request = self.factory.post(
            reverse('fetch-languages')
        )
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 201)

        view = LanguageList.as_view()
        request = self.factory.get(
            reverse('language-list') + '?cached=false'
        )
        request.user = user
        response = view(request)
        self.assertEqual(response.data[0]['code'], 'EN')
        self.assertEqual(response.data[1]['code'], 'JA')

    def test_fetch_dataset_admin_level_names(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create(
            label='Dataset World'
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset,
            level=0
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset,
            level=1
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse('dataset-admin-level-names', kwargs=kwargs)
        )
        request.user = user
        view = DatasetAdminLevelNames.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_update_dataset_admin_level_names(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create(
            label='Dataset World'
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset,
            level=0
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset,
            level=1
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        data = [
            {
                'label': 'test-level-0',
                'level': 0
            },
            {
                'label': 'Province-1',
                'level': 1
            },
            {
                'label': 'District-2',
                'level': 2
            }
        ]
        request = self.factory.post(
            reverse('dataset-admin-level-names', kwargs=kwargs),
            data=data, format='json'
        )
        request.user = user
        view = DatasetAdminLevelNames.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset,
            level=0
        ).first()
        self.assertEqual(updated.label, 'test-level-0')
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset,
            level=1
        ).first()
        self.assertEqual(updated.label, 'Province-1')
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset,
            level=2
        ).first()
        self.assertEqual(updated.label, 'District-2')
        # test duplicate
        dataset2 = DatasetF.create(
            label='Dataset World'
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset2,
            level=0
        )
        DatasetAdminLevelNameF.create(
            dataset=dataset2,
            level=1
        )
        kwargs = {
            'uuid': str(dataset2.uuid)
        }
        data = [
            {
                'label': 'test-level-0',
                'level': 1
            },
            {
                'label': 'Province-1',
                'level': 1
            }
        ]
        request = self.factory.post(
            reverse('dataset-admin-level-names', kwargs=kwargs),
            data=data, format='json'
        )
        request.user = user
        view = DatasetAdminLevelNames.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset2,
            level=0
        ).first()
        self.assertEqual(updated.label, 'Level-0')
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset2,
            level=1
        ).first()
        self.assertEqual(updated.label, 'Level-1')
        # test delete
        data = [
            {
                'label': 'test-level-0',
                'level': 0
            }
        ]
        request = self.factory.post(
            reverse('dataset-admin-level-names', kwargs=kwargs),
            data=data, format='json'
        )
        request.user = user
        view = DatasetAdminLevelNames.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset2,
            level=0
        ).first()
        self.assertEqual(updated.label, 'test-level-0')
        updated = DatasetAdminLevelName.objects.filter(
            dataset=dataset2,
            level=1
        ).first()
        self.assertFalse(updated)

    def test_fetch_tiling_configs(self):
        dataset = DatasetF.create()
        populate_tile_configs(dataset.id)
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse('fetch-tiling-configs', kwargs=kwargs)
        )
        # should return ok
        request.user = self.superuser
        query_view = FetchDatasetTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 9)

    def test_fetch_view_tiling_configs(self):
        user = UserF.create()
        dataset = DatasetF.create()
        populate_tile_configs(dataset.id)
        view = DatasetViewF.create(
            dataset=dataset
        )
        kwargs = {
            'view': str(view.uuid)
        }
        request = self.factory.get(
            reverse('fetch-view-tiling-configs', kwargs=kwargs)
        )
        # should return ok
        request.user = user
        query_view = FetchDatasetViewTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 9)

    @mock.patch(
        'dashboard.api_views.tiling_config.'
        'simplify_geometry_in_dataset.delay',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    @mock.patch('dashboard.api_views.tiling_config.app.control.revoke',
                mock.Mock(side_effect=mocked_revoke_running_task))
    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_update_tiling_configs(self):
        dataset = DatasetF.create()
        populate_tile_configs(dataset.id)
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        tiling_config_path = absolute_path(
            'dashboard', 'tests',
            'tiling_config_data',
            'tiling_config_test.json')
        with open(tiling_config_path) as json_file:
            data = json.load(json_file)
        request = self.factory.post(
            reverse('update-tiling-configs', kwargs=kwargs),
            data, format='json'
        )
        # should return ok
        request.user = self.superuser
        query_view = UpdateDatasetTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        admin_levels = AdminLevelTilingConfig.objects.filter(
            dataset_tiling_config__dataset=dataset,
            dataset_tiling_config__zoom_level=4
        )
        self.assertEqual(admin_levels.count(), 1)
        tiling_config_path = absolute_path(
            'dashboard', 'tests',
            'tiling_config_data',
            'tiling_config_test_error.json')
        with open(tiling_config_path) as json_file:
            data = json.load(json_file)
        request = self.factory.post(
            reverse('update-tiling-configs', kwargs=kwargs),
            data, format='json'
        )
        # should return error
        request.user = self.superuser
        query_view = UpdateDatasetTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 400)

    @mock.patch(
        'dashboard.api_views.tiling_config.'
        'trigger_generate_vector_tile_for_view',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    @mock.patch(
        'dashboard.api_views.tiling_config.simplify_geometry_in_view.delay',
        mock.Mock(side_effect=mocked_run_generate_vector_tiles)
    )
    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_update_view_tiling_configs(self):
        user = UserF.create()
        dataset = DatasetF.create()
        populate_tile_configs(dataset.id)
        view = DatasetViewF.create(
            dataset=dataset
        )
        kwargs = {
            'view': str(view.uuid)
        }
        tiling_config_path = absolute_path(
            'dashboard', 'tests',
            'tiling_config_data',
            'tiling_config_test.json')
        with open(tiling_config_path) as json_file:
            data = json.load(json_file)
        request = self.factory.post(
            reverse('update-view-tiling-configs', kwargs=kwargs),
            data, format='json'
        )
        # should return ok
        request.user = user
        query_view = UpdateDatasetViewTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        # admin_levels = ViewAdminLevelTilingConfig.objects.filter(
        #     dataset_tiling_config__dataset=dataset,
        #     dataset_tiling_config__zoom_level=4
        # )
        # self.assertEqual(admin_levels.count(), 1)
        tiling_config_path = absolute_path(
            'dashboard', 'tests',
            'tiling_config_data',
            'tiling_config_test_error.json')
        with open(tiling_config_path) as json_file:
            data = json.load(json_file)
        request = self.factory.post(
            reverse('update-view-tiling-configs', kwargs=kwargs),
            data, format='json'
        )
        # should return error
        request.user = user
        query_view = UpdateDatasetViewTilingConfig.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 400)

    def test_fetch_dataset_boundary_types(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create(
            label='Dataset World'
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        request = self.factory.get(
            reverse('dataset-boundary-types', kwargs=kwargs)
        )
        request.user = user
        view = DatasetBoundaryTypes.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        type_0 = BoundaryTypeF.create(
            dataset=dataset,
            value='0'
        )
        BoundaryTypeF.create(
            dataset=dataset,
            value='1'
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['total_entities'], 0)
        self.assertEqual(response.data[1]['total_entities'], 0)
        GeographicalEntityF.create(
            dataset=dataset,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='CODE_0',
            unique_code='CODE_0',
            revision_number=1,
            type=type_0.type,
            level=0
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['value'], '0')
        self.assertEqual(response.data[0]['total_entities'], 1)
        self.assertEqual(response.data[1]['total_entities'], 0)

    def test_update_dataset_boundary_types(self):
        user = UserF.create(is_superuser=True)
        dataset = DatasetF.create(
            label='Dataset World'
        )
        kwargs = {
            'uuid': str(dataset.uuid)
        }
        entity_type_0 = EntityTypeF.create(
            label='test_0'
        )
        type_0 = BoundaryTypeF.create(
            dataset=dataset,
            type=entity_type_0,
            value='0'
        )
        type_1 = BoundaryTypeF.create(
            dataset=dataset,
            value='1'
        )
        post_data = [
            {
                'id': type_0.id,
                'label': 'updated_0',
                'type_id': entity_type_0.id,
                'value': 'value_0'
            },
            {
                'id': 0,
                'label': 'new_2',
                'type_id': 0,
                'value': 'new_value_2'
            }
        ]
        request = self.factory.post(
            reverse('dataset-boundary-types', kwargs=kwargs),
            data=post_data, format='json'
        )
        request.user = user
        view = DatasetBoundaryTypes.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 204)
        updated = BoundaryType.objects.get(id=type_0.id)
        self.assertEqual(updated.value, post_data[0]['value'])
        self.assertEqual(updated.type.label, post_data[0]['label'])
        self.assertFalse(
            BoundaryType.objects.filter(id=type_1.id).exists()
        )
        new_value = BoundaryType.objects.filter(
            value='new_value_2'
        ).first()
        self.assertTrue(new_value)

    def test_get_entity_by_cucode(self):
        dataset = DatasetF.create(
            module=self.module
        )
        entity1 = GeographicalEntityF.create(
            level=0,
            uuid=str(uuid.uuid4()),
            dataset=dataset,
            is_latest=True,
            is_approved=True,
            label='Test',
            revision_number=1,
            internal_code='PAK',
            unique_code='PAK',
            unique_code_version='1',
            concept_ucode='#PAK_1',
            uuid_revision=str(uuid.uuid4())
        )
        kwargs = {
            'concept_ucode': entity1.concept_ucode
        }
        request = self.factory.get(
            reverse('entity-by-concept-ucode', kwargs=kwargs)
        )
        test_user = UserF.create(
            is_superuser=True
        )
        request.user = test_user
        view = EntityByConceptUCode.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['entities']), 1)

    @override_settings(
        GEOJSON_FOLDER_OUTPUT=(
            '/home/web/django_project/georepo/tests/dataset_export'
        )
    )
    def test_download_view(self):
        dataset = DatasetF.create(
            label='ABC'
        )
        generate_default_view_dataset_latest(dataset)
        dataset_view = DatasetView.objects.filter(
            dataset=dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(dataset_view)
        resource = dataset_view.datasetviewresource_set.filter(
            privacy_level=4
        ).first()
        resource.uuid = uuid.UUID('e59f8338-e8a8-4e6d-9e0d-c63108a8048e')
        resource.save()
        parent = GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK',
            unique_code_version=1
        )
        GeographicalEntityF.create(
            dataset=dataset_view.dataset,
            level=1,
            parent=parent,
            ancestor=parent,
            is_latest=True,
            is_approved=True,
            version=1,
            unique_code='PAK_001',
            unique_code_version=1
        )
        kwargs = {
            'id': str(dataset_view.id)
        }
        request = self.factory.get(
            reverse(
                'view-download',
                kwargs=kwargs
            )
        )
        view = DownloadView.as_view()
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get('Content-Disposition'),
            f'attachment; filename="{dataset_view.name}.zip"'
        )
