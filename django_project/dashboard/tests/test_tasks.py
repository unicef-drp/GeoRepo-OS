import mock
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from core.settings.utils import absolute_path
from georepo.models.id_type import IdType
from dashboard.models.layer_upload_session import (
    LayerUploadSession, PENDING, UPLOAD_PROCESS_COUNTRIES_SELECTION,
    LayerUploadSessionActionLog, LayerUploadSessionMetadata, DONE
)
from dashboard.models.entity_upload import (
    EntityUploadStatus, STARTED, REVIEWING
)
from georepo.tests.model_factories import (
    LanguageF, GeographicalEntityF, ModuleF, DatasetF
)
from dashboard.tests.model_factories import (
    LayerFileF,
    LayerUploadSessionF,
    EntityUploadF,
    EntityUploadChildLv1F
)
from dashboard.tasks import (
    layer_upload_preprocessing,
    process_country_selection
)


def mocked_load_geojson_error(*args, **kwargs):
    return False, 'Error'


def mocked_load_geojson_success(*args, **kwargs):
    return True, ''


def mocked_revoke_running_task(*args, **kwargs):
    return True


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_task(*args, **kwargs):
    return DummyTask('1')


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
        metadata = LayerUploadSessionMetadata.objects.filter(
            session=upload_session
        ).first()
        self.assertTrue(metadata)
        self.assertEqual(len(metadata.adm0_default_codes), 1)


    @mock.patch('dashboard.tasks.upload.app.control.revoke',
                mock.Mock(side_effect=mocked_revoke_running_task))
    @mock.patch(
        'dashboard.tasks.upload.validate_ready_uploads.apply_async',
        mock.Mock(side_effect=mocked_run_task)
    )
    def test_process_country_selection(self):
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
        data = {
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
        session_action = LayerUploadSessionActionLog.objects.create(
            session=upload_session_0,
            action=UPLOAD_PROCESS_COUNTRIES_SELECTION,
            data=data
        )
        process_country_selection(session_action.id)
        updated_upload_0 = EntityUploadStatus.objects.get(
            id=entity_upload_0.id
        )
        self.assertEqual(updated_upload_0.status, STARTED)
        self.assertEqual(updated_upload_0.max_level, '2')
        session_action = LayerUploadSessionActionLog.objects.get(
            id=session_action.id
        )
        self.assertEqual(session_action.status, DONE)
        self.assertIn('is_valid', session_action.result)
        self.assertTrue(session_action.result['is_valid'])
        # upload admin level 1, has existing country, rematched
        upload_session_1 = LayerUploadSessionF.create(
            dataset=dataset
        )
        entity_upload_1 = EntityUploadF.create(
            upload_session=upload_session_1,
            status=''
        )
        EntityUploadChildLv1F.create(
            entity_upload=entity_upload_1,
            entity_id='PAK001',
            entity_name='PAK_001',
            parent_entity_id='PAQ',
            is_parent_rematched=True
        )
        ori_entity_1 = entity_upload_1.original_geographical_entity
        ori_entity_1.internal_code = 'PAK'
        ori_entity_1.save()
        data = {
            'entities': [{
                'id': ori_entity_1.id,
                'layer0_id': ori_entity_1.internal_code,
                'country_entity_id': ori_entity_1.id,
                'max_level': 1,
                'country': ori_entity_1.label,
                'upload_id': entity_upload_1.id,
                'admin_level_names': {}
            }]
        }
        session_action = LayerUploadSessionActionLog.objects.create(
            session=upload_session_1,
            action=UPLOAD_PROCESS_COUNTRIES_SELECTION,
            data=data
        )
        process_country_selection(session_action.id)
        updated_upload_1 = EntityUploadStatus.objects.get(
            id=entity_upload_1.id
        )
        self.assertEqual(updated_upload_1.status, STARTED)
        self.assertEqual(updated_upload_1.max_level, '1')
        session_action = LayerUploadSessionActionLog.objects.get(
            id=session_action.id
        )
        self.assertEqual(session_action.status, DONE)
        self.assertIn('is_valid', session_action.result)
        self.assertTrue(session_action.result['is_valid'])
        # upload admin level 1, but the country has review in progress
        upload_session_2 = LayerUploadSessionF.create(
            dataset=upload_session_1.dataset
        )
        # reset prev status
        entity_upload_1.status = ''
        entity_upload_1.save()
        entity_upload_2 = EntityUploadF.create(
            status=REVIEWING,
            original_geographical_entity=ori_entity_1,
            upload_session=upload_session_2
        )
        data = {
            'entities': [{
                'id': ori_entity_1.id,
                'layer0_id': ori_entity_1.internal_code,
                'country_entity_id': ori_entity_1.id,
                'max_level': 1,
                'country': ori_entity_1.label,
                'upload_id': entity_upload_1.id,
                'admin_level_names': {}
            }]
        }
        session_action = LayerUploadSessionActionLog.objects.create(
            session=upload_session_1,
            action=UPLOAD_PROCESS_COUNTRIES_SELECTION,
            data=data
        )
        process_country_selection(session_action.id)
        updated_upload_2 = EntityUploadStatus.objects.get(
            id=entity_upload_2.id
        )
        self.assertEqual(updated_upload_2.status, REVIEWING)
        session_action = LayerUploadSessionActionLog.objects.get(
            id=session_action.id
        )
        self.assertEqual(session_action.status, DONE)
        self.assertIn('is_valid', session_action.result)
        self.assertFalse(session_action.result['is_valid'])
