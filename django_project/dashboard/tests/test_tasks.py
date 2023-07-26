from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from core.settings.utils import absolute_path
from georepo.models.id_type import IdType
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PENDING
)
from dashboard.models.entity_upload import (
    EntityUploadStatus
)
from georepo.tests.model_factories import (
    LanguageF, GeographicalEntityF, ModuleF, DatasetF
)
from dashboard.tests.model_factories import (
    LayerFileF,
    LayerUploadSessionF,
    EntityUploadF
)
from dashboard.tasks import layer_upload_preprocessing


def mocked_load_geojson_error(*args, **kwargs):
    return False, 'Error'


def mocked_load_geojson_success(*args, **kwargs):
    return True, ''


class TestTasks(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.language = LanguageF.create()
        self.idType = IdType.objects.create(
            name='PCode'
        )
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_layer_upload_preprocessing(self):
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        LayerFileF.create(
            layer_upload_session=upload_session,
            level='0',
            parent_id_field='',
            entity_type='Country',
            name_fields=[
                {
                    'field': 'name_0',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_0',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
            layer_file=(
                absolute_path('dashboard', 'tests',
                              'parent_matching_dataset',
                              'level_0.geojson')
            )
        )
        LayerFileF.create(
            layer_upload_session=upload_session,
            level=1,
            parent_id_field='code_0',
            location_type_field='type',
            name_fields=[
                {
                    'field': 'adm1_name',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_1',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
            layer_file=(
                absolute_path('dashboard', 'tests',
                              'parent_matching_dataset',
                              'level_1.geojson')
            )
        )
        geo_1 = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            internal_code='PAK'
        )
        upload_1 = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_1
        )
        upload_2 = EntityUploadF.create(
            upload_session=upload_session,
            revised_entity_id='IND',
            revised_entity_name='India'
        )
        layer_upload_preprocessing(upload_session.id)
        self.assertFalse(EntityUploadStatus.objects.filter(
            id=upload_1.id
        ).exists())
        self.assertFalse(EntityUploadStatus.objects.filter(
            id=upload_2.id
        ).exists())
        updated_session = LayerUploadSession.objects.get(
            id=upload_session.id
        )
        self.assertEqual(updated_session.status, PENDING)
        uploads = updated_session.entityuploadstatus_set.all()
        self.assertEqual(len(uploads), 1)

    # @mock.patch(
    #     'dashboard.api_views.layer_upload.process_layer_upload_session.delay',
    #     mock.Mock(side_effect=mocked_process_layer_upload_session))
    # @mock.patch('dashboard.tasks.load_geojson',
    #             mock.Mock(side_effect=mocked_load_geojson_success))
    # def test_process_layer_upload_session_task_success(self):
    #     uploader = UserF.create(username='uploader')
    #     layer_file_1 = LayerFileF.create(
    #         meta_id='test_1',
    #         uploader=uploader)
    #     layer_file_2 = LayerFileF.create(meta_id='test_2', uploader=uploader)
    #     post_data = {
    #         'entity_types': {
    #             layer_file_1.meta_id: 'Country',
    #             layer_file_2.meta_id: 'Region'
    #         },
    #         'levels': {
    #             layer_file_1.meta_id: '0',
    #             layer_file_2.meta_id: '1'
    #         },
    #         'all_files': [
    #             {
    #                 'id': layer_file_1.meta_id,
    #             },
    #             {
    #                 'id': layer_file_2.meta_id,
    #             }
    #         ],
    #         'dataset': 'dataset_name',
    #         'code_format': 'code_{level}',
    #         'label_format': 'admin_{level}'
    #     }
    #     request = self.factory.post(
    #         reverse('layers-process'), post_data,
    #         format='json'
    #     )
    #     request.user = UserF.create(username='test')
    #     view = LayersProcessView.as_view()
    #     response = view(request)
    #     self.assertEqual(response.status_code, 200)
    #
    #     upload_session = LayerUploadSession.objects.get(
    #         dataset='dataset_name',
    #     )
    #     process_layer_upload_session(upload_session.id)
    #     self.assertTrue(
    #         LayerUploadSession.objects.get(
    #             dataset='dataset_name'
    #         ).status == DONE
    #     )
    #
    # @mock.patch(
    #     'dashboard.api_views.layer_upload.process_layer_upload_session.delay',
    #     mock.Mock(side_effect=mocked_process_layer_upload_session))
    # @mock.patch('dashboard.tasks.load_geojson',
    #             mock.Mock(side_effect=mocked_load_geojson_error))
    # def test_process_layer_upload_session_task_error(self):
    #     uploader = UserF.create(username='uploader')
    #     layer_file_1 = LayerFileF.create(
    #         meta_id='test_1',
    #         uploader=uploader)
    #     layer_file_2 = LayerFileF.create(meta_id='test_2', uploader=uploader)
    #     post_data = {
    #         'entity_types': {
    #             layer_file_1.meta_id: 'Country',
    #             layer_file_2.meta_id: 'Region'
    #         },
    #         'levels': {
    #             layer_file_1.meta_id: '0',
    #             layer_file_2.meta_id: '1'
    #         },
    #         'all_files': [
    #             {
    #                 'id': layer_file_1.meta_id,
    #             },
    #             {
    #                 'id': layer_file_2.meta_id,
    #             }
    #         ],
    #         'dataset': 'dataset_name',
    #         'code_format': 'code_{level}',
    #         'label_format': 'admin_{level}'
    #     }
    #     request = self.factory.post(
    #         reverse('layers-process'), post_data,
    #         format='json'
    #     )
    #     request.user = UserF.create(username='test')
    #     view = LayersProcessView.as_view()
    #     response = view(request)
    #     self.assertEqual(response.status_code, 200)
    #
    #     upload_session = LayerUploadSession.objects.get(
    #         dataset='dataset_name',
    #     )
    #     process_layer_upload_session(upload_session.id)
    #     self.assertTrue(
    #         LayerUploadSession.objects.get(
    #             dataset='dataset_name'
    #         ).status == ERROR
    #     )
