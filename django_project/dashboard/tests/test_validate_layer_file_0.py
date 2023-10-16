from django.test import TestCase, override_settings

from core.settings.utils import absolute_path
from georepo.tests.model_factories import (
    LanguageF, GeographicalEntityF
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from dashboard.tools.validate_layer_file_0 import \
    validate_layer_file_0, preprocess_layer_file_0
from georepo.utils.layers import read_layer_files_entity_temp


class TestValidateLayerFile0(TestCase):

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_validate_layer_file_0(self):
        geojson_1 = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset',
            'level_0_1.geojson')
        geojson_2 = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset',
            'level_0_2.geojson')
        language = LanguageF.create()
        upload_session = LayerUploadSessionF.create()
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            level=0,
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
            layer_file=geojson_1
        )
        is_valid, duplicate = validate_layer_file_0(upload_session)
        self.assertTrue(is_valid)
        self.assertFalse(duplicate)
        layer_file.layer_file = geojson_2
        layer_file.save()
        is_valid, duplicate = validate_layer_file_0(upload_session)
        self.assertFalse(is_valid)
        self.assertEqual(duplicate, 'PAK')

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_preprocess_layer_file_0(self):
        geojson_1 = absolute_path(
            'dashboard', 'tests',
            'geojson_dataset',
            'level_0_3.geojson')
        language = LanguageF.create()
        upload_session = LayerUploadSessionF.create()
        LayerFileF.create(
            layer_upload_session=upload_session,
            level=0,
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
            layer_file=geojson_1
        )
        parent_1 = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            internal_code='PAK'
        )
        GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            internal_code='AGO'
        )
        read_layer_files_entity_temp(upload_session)
        entity_uploads = preprocess_layer_file_0(upload_session)
        self.assertEqual(len(entity_uploads), 2)
        self.assertTrue(entity_uploads[0].original_geographical_entity)
        self.assertEqual(
            entity_uploads[0].original_geographical_entity.internal_code,
            parent_1.internal_code
        )
        self.assertFalse(entity_uploads[1].original_geographical_entity)
        self.assertEqual(
            entity_uploads[1].revised_entity_id,
            'IND'
        )
