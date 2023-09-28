import mock
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from core.settings.utils import absolute_path
from georepo.tests.model_factories import (
    LanguageF, ModuleF, DatasetF
)
from dashboard.models import (
    LayerUploadSession, UPLOAD_PROCESS_COUNTRIES_SELECTION
)
from dashboard.tests.model_factories import (
    LayerUploadSessionF, LayerFileF, EntityUploadF
)
from dashboard.api_views.validate import (
    ValidateUploadSession,
    LayerUploadPreprocess
)


def mocked_auto_parent_matching(*args, **kwargs):
    print(f'mocked task: {args[0]}')
    upload = LayerUploadSession.objects.get(id=args[0])
    upload.auto_matched_parent_ready = True
    upload.status = 'Pending'
    upload.save()
    return DummyTask('1')


def mocked_revoke_running_task(*args, **kwargs):
    return True


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_task(*args, **kwargs):
    return DummyTask('1')


class TestValidateApiViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )

    @mock.patch(
        'dashboard.api_views.validate.layer_upload_preprocessing.delay',
        mock.Mock(side_effect=mocked_auto_parent_matching)
    )
    @mock.patch('dashboard.api_views.validate.app.control.revoke',
                mock.Mock(side_effect=mocked_revoke_running_task))
    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_layer_upload_preprocess(self):
        geojson_0 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_0.geojson')
        geojson_1 = absolute_path(
            'dashboard', 'tests',
            'parent_matching_dataset',
            'level_1.geojson')
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session_0 = LayerUploadSessionF.create(
            dataset=dataset
        )
        language = LanguageF.create()
        LayerFileF.create(
            layer_upload_session=upload_session_0,
            meta_id='test_0',
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
            layer_file=geojson_0)
        LayerFileF.create(
            layer_upload_session=upload_session_0,
            meta_id='test_0_1',
            level='1',
            parent_id_field='code_0',
            entity_type='Region',
            name_fields=[
                {
                    'field': 'name_1',
                    'default': True,
                    'selectedLanguage': language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_1',
                    'default': True
                }
            ],
            layer_file=geojson_1)
        request = self.factory.post(
            reverse('layer-upload-preprocess'), {
                'upload_session': upload_session_0.id
            }
        )
        request.user = upload_session_0.uploader
        view = LayerUploadPreprocess.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        updated_session_0 = LayerUploadSession.objects.get(
            id=upload_session_0.id
        )
        self.assertTrue(updated_session_0.auto_matched_parent_ready)
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session_1 = LayerUploadSessionF.create(
            dataset=dataset
        )
        LayerFileF.create(
            layer_upload_session=upload_session_1,
            meta_id='test_1_1',
            level='1',
            parent_id_field='code_0',
            entity_type='Region',
            name_fields=[
                {
                    'field': 'name_1',
                    'default': True,
                    'selectedLanguage': language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_1',
                    'default': True
                }
            ],
            layer_file=geojson_1)
        request = self.factory.post(
            reverse('layer-upload-preprocess'), {
                'upload_session': upload_session_1.id
            }
        )
        request.user = upload_session_1.uploader
        view = LayerUploadPreprocess.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        updated_session_1 = LayerUploadSession.objects.get(
            id=upload_session_1.id
        )
        self.assertEqual(updated_session_1.auto_matched_parent_ready, True)

    @mock.patch(
        'dashboard.api_views.validate.process_country_selection.delay',
        mock.Mock(side_effect=mocked_run_task)
    )
    def test_validate_upload_session(self):
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session_0 = LayerUploadSessionF.create(
            dataset=dataset
        )
        entity_upload_0 = EntityUploadF.create(
            upload_session=upload_session_0,
            original_geographical_entity=None,
            status='',
            revised_entity_id='PAK',
            revised_entity_name='Pakistan'
        )
        # upload admin level 0, no existing country
        post_data = {
            'upload_session': upload_session_0.id,
            'entities': [{
                'id': 'random',
                'layer0_id': entity_upload_0.revised_entity_id,
                'country_entity_id': None,
                'max_level': 2,
                'country': entity_upload_0.revised_entity_name,
                'upload_id': entity_upload_0.id,
                'admin_level_names': {}
            }]
        }
        request = self.factory.post(
            reverse('validate-upload-session'), post_data,
            format='json'
        )
        request.user = upload_session_0.uploader
        view = ValidateUploadSession.as_view()
        response = view(request)
        self.assertEqual(response.status_code, 200)
        updated_session_0 = LayerUploadSession.objects.get(
            id=upload_session_0.id
        )
        self.assertEqual(updated_session_0.current_process,
                         UPLOAD_PROCESS_COUNTRIES_SELECTION)
        self.assertTrue(updated_session_0.current_process_uuid)
        self.assertEqual(updated_session_0.current_process_uuid,
                         response.data['action_uuid'])
