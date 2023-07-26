from django.test import TestCase, override_settings

from core.settings.utils import absolute_path
from georepo.models.id_type import IdType
from dashboard.models.entity_upload import (
    EntityUploadStatus
)
from georepo.tests.model_factories import (
    LanguageF, GeographicalEntityF
)
from dashboard.tests.model_factories import (
    LayerFileF,
    LayerUploadSessionF,
    EntityUploadF
)
from dashboard.tools.find_country_max_level import (
    find_country_max_level
)


class TestFindCountryMaxLevel(TestCase):

    def setUp(self):
        self.language = LanguageF.create()
        self.idType = IdType.objects.create(
            name='PCode'
        )

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_find_country_max_level(self):
        upload_session = LayerUploadSessionF.create()
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
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_1_1.geojson')
            )
        )
        LayerFileF.create(
            layer_upload_session=upload_session,
            level='2',
            location_type_field='type',
            parent_id_field='code_1',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_2_1.geojson')
            ),
            name_fields=[
                {
                    'field': 'adm2_name',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'code_2',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
        )
        geo_1 = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            internal_code='VCT'
        )
        upload_1 = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_1
        )
        geo_2 = GeographicalEntityF.create(
            dataset=upload_session.dataset,
            level=0,
            is_latest=True,
            is_approved=True,
            internal_code='PAK'
        )
        upload_2 = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geo_2
        )
        find_country_max_level(upload_session, False)
        updated = EntityUploadStatus.objects.get(id=upload_1.id)
        self.assertEqual(updated.max_level_in_layer, '2')
        updated = EntityUploadStatus.objects.get(id=upload_2.id)
        self.assertEqual(updated.max_level_in_layer, '1')

    @override_settings(MEDIA_ROOT='/home/web/django_project/dashboard')
    def test_find_country_max_level_at_0(self):
        upload_session = LayerUploadSessionF.create()
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
                              'geojson_dataset', 'level_0_3.geojson')
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
                              'geojson_dataset', 'level_1_1.geojson')
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
        find_country_max_level(upload_session, True)
        updated = EntityUploadStatus.objects.get(id=upload_1.id)
        self.assertEqual(updated.max_level_in_layer, '1')
        updated = EntityUploadStatus.objects.get(id=upload_2.id)
        self.assertEqual(updated.max_level_in_layer, '0')
