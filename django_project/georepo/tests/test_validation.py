import json
import os.path
import mock

from django.contrib.gis.geos import GEOSGeometry
from django.test import TestCase, override_settings, TransactionTestCase
from django.db import transaction, IntegrityError

from django.utils import timezone
from georepo.models import (
    GeographicalEntity, IdType, EntityType,
    EntityName, EntityId
)
from georepo.tests.model_factories import (
    DatasetF, LanguageF, GeographicalEntityF,
    UserF, ModuleF, EntityTypeF
)
from georepo.utils import absolute_path
from dashboard.models.entity_upload import (
    EntityUploadStatus, STARTED, PROCESSING, WARNING
)
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    LayerFileF,
    EntityUploadF,
    EntityUploadChildLv1F
)
from georepo.validation.error_type import ErrorType
from georepo.validation.layer_validation import (
    validate_layer_file,
    get_hierarchical_from_layer_file,
    search_hierarchical,
    validate_level_country,
    retrieve_layer0_default_codes,
    validate_level_admin_1,
    read_layer_files
)
from georepo.tasks.validation import find_entity_upload
from georepo.utils.layers import read_layer_files_entity_temp

ERROR_REPORT_PATH = '/home/web/django_project/georepo/error_reports/'


def mock_geom_covers(geom):
    return True


class TestValidation(TestCase):

    def setUp(self) -> None:
        if not os.path.exists(ERROR_REPORT_PATH):
            os.mkdir(ERROR_REPORT_PATH)
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module
        )
        self.language = LanguageF.create()
        self.upload_session = LayerUploadSessionF.create(
            dataset=self.dataset,
            tolerance=1e-8,
            overlaps_threshold=0.01,
            gaps_threshold=0.01
        )
        self.idType = IdType.objects.create(
            name='PCode'
        )
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geographical_entity = GeographicalEntityF.create(
                dataset=self.dataset,
                is_validated=True,
                is_approved=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                revision_number=1
            )

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(
            ERROR_REPORT_PATH
        )

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_layer_file(self):
        layer_file_1 = LayerFileF.create(
            layer_upload_session=self.upload_session,
            level='1',
            parent_id_field='iso3',
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
                              'geojson_dataset', 'level_1.geojson')
            )
        )
        layer_file_2 = LayerFileF.create(
            layer_upload_session=self.upload_session,
            level='2',
            location_type_field='type',
            parent_id_field='code_1',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_2.geojson')
            ),
            name_fields=[
                {
                    'field': 'adm2_name',
                    'default': True,
                    'selectedLanguage': self.language.id,
                    'label': 'Name 1'
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
        )

        self.assertTrue(os.path.exists(layer_file_1.layer_file.path))
        self.assertTrue(os.path.exists(layer_file_2.layer_file.path))

        entity_upload = EntityUploadF.create(
            upload_session=self.upload_session,
            original_geographical_entity=self.geographical_entity
        )
        read_layer_files_entity_temp(self.upload_session)

        status = validate_layer_file(
            entity_upload=entity_upload
        )

        updated_entity_upload = EntityUploadStatus.objects.get(
            id=entity_upload.id
        )
        self.assertTrue(status)
        self.assertTrue(updated_entity_upload.revised_geographical_entity)
        entity_lvl1 = GeographicalEntity.objects.filter(
            parent__revision_number=2,
            revision_number=2,
            level=1,
            label='Khyber Pakhtunkhwa',
            is_approved=None,
            is_validated=False
        )
        self.assertTrue(entity_lvl1.exists())
        entity = entity_lvl1.first()
        self.assertTrue(entity.centroid)
        self.assertTrue(entity.bbox)
        entity_lvl2 = GeographicalEntity.objects.filter(
            parent__label='Khyber Pakhtunkhwa',
            level=2,
            label='Lakki Marwat Tsd',
            is_approved=None,
            is_validated=False
        )
        self.assertTrue(entity_lvl2.exists())
        entity = entity_lvl2.first()
        self.assertTrue(entity.centroid)
        self.assertTrue(entity.bbox)
        names = entity.entity_names.all()
        self.assertEqual(names.count(), 1)
        self.assertEqual(names[0].name, 'Lakki Marwat Tsd')
        self.assertEqual(names[0].label, 'Name 1')

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_self_intersects_layer_file(self):
        layer_file = LayerFileF.create(
            layer_upload_session=self.upload_session,
            level='1',
            parent_id_field='iso3',
            location_type_field='adm1_name',
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
                              'geojson_dataset',
                              'geojson_1_self_intersects.geojson')
            )
        )

        entity_upload = EntityUploadF.create(
            upload_session=self.upload_session,
            original_geographical_entity=self.geographical_entity
        )
        read_layer_files_entity_temp(self.upload_session)

        status = validate_layer_file(
            entity_upload=entity_upload
        )
        entity_upload.refresh_from_db()
        self.assertEqual(
            entity_upload.summaries[0][
                ErrorType.SELF_INTERSECTS.value],
            1
        )
        self.assertFalse(status)
        self.assertEqual(entity_upload.status, WARNING)
        # entities in error upload will be deleted
        # if not selected to be imported
        self.assertTrue(GeographicalEntity.objects.filter(
            layer_file=layer_file
        ).exists())

    def do_validate_layer_from_level_0(self):
        dataset = DatasetF.create(
            module=self.module
        )
        superuser = UserF.create(is_superuser=True)
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=superuser
        )
        layer_file = LayerFileF.create(
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
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_0.geojson')
            )
        )
        layer_file_1 = LayerFileF.create(
            layer_upload_session=upload_session,
            level='1',
            parent_id_field='iso3',
            location_type_field='type',
            name_fields=[
                {
                    'field': 'name_1',
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
                              'geojson_dataset', 'level_1.geojson')
            )
        )
        entity_upload = EntityUploadF.create(
            original_geographical_entity=None,
            upload_session=upload_session,
            revised_entity_id='PAK',
            admin_level_names={
                '0': 'CountryF',
                '1': 'ProvinceF',
                '2': 'DistrictF'
            }
        )
        read_layer_files_entity_temp(upload_session)
        status = validate_layer_file(entity_upload)
        layer_files = [layer_file, layer_file_1]
        return status, layer_files, upload_session, entity_upload

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_layer_level_0(self):
        status, layer_files, _, _ = (
            self.do_validate_layer_from_level_0()
        )
        self.assertTrue(status)
        layer_file = layer_files[0]
        layer_file_1 = layer_files[1]
        self.assertTrue(
            GeographicalEntity.objects.filter(
                internal_code='PAK',
                is_approved=None,
                layer_file_id=layer_file.id,
                admin_level_name='CountryF'
            ).exists()
        )
        self.assertTrue(
            GeographicalEntity.objects.filter(
                parent__internal_code='PAK',
                is_approved=None,
                layer_file_id=layer_file_1.id,
                admin_level_name='ProvinceF'
            ).exists()
        )
        self.assertEqual(
            EntityName.objects.count(), 2
        )
        self.assertEqual(
            EntityId.objects.count(), 2
        )

    def test_multiple_entity_types_unique_constraint(self):
        # create multiple EntityTypes of Country, it will raise Exception
        type1 = EntityTypeF.create(
            label='Country'
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                EntityTypeF.create(
                    label='Country'
                )
        # test get_by_label
        type2 = EntityType.objects.get_by_label('Country')
        self.assertEqual(type1.id, type2.id)
        # test the integrityError in get_by_label
        with mock.patch(
                'georepo.models.EntityType.objects.filter') as mocked_filter:
            mocked_filter.return_value = EntityType.objects.none()
            type2 = EntityType.objects.get_by_label('Country')
            self.assertEqual(type1.id, type2.id)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_get_hierarchical_from_layer_file(self):
        layer_file_1 = LayerFileF.create(
            layer_upload_session=self.upload_session,
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
        layer_file_2 = LayerFileF.create(
            layer_upload_session=self.upload_session,
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
        layer_files = [layer_file_1, layer_file_2]
        layer_cache = read_layer_files(layer_files)
        result = get_hierarchical_from_layer_file(
            layer_files,
            1,
            'PAK',
            layer_cache
        )
        self.assertEqual(len(result), 1)
        result = get_hierarchical_from_layer_file(
            layer_files,
            2,
            'PAK003',
            layer_cache
        )
        self.assertEqual(len(result), 0)
        result = get_hierarchical_from_layer_file(
            layer_files,
            2,
            'AUT-20200921-8',
            layer_cache
        )
        self.assertEqual(len(result), 2)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_search_hierarchical(self):
        layer_file_1 = LayerFileF.create(
            layer_upload_session=self.upload_session,
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
        layer_file_2 = LayerFileF.create(
            layer_upload_session=self.upload_session,
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
        layer_file_3 = LayerFileF.create(
            layer_upload_session=self.upload_session,
            level='3',
            location_type_field='type',
            parent_id_field='code_2',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_3_1.geojson')
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
                    'field': 'code_3',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
        )
        layer_files = [layer_file_1, layer_file_2, layer_file_3]
        layer_cache = read_layer_files(layer_files)
        result = search_hierarchical(
            1,
            1,
            'PAK',
            layer_files,
            layer_cache
        )
        self.assertTrue(result)
        result = search_hierarchical(
            2,
            1,
            'ABCCC',
            layer_files,
            layer_cache
        )
        self.assertFalse(result)
        result = search_hierarchical(
            2,
            1,
            'AUT',
            layer_files,
            layer_cache
        )
        self.assertTrue(result)
        result = search_hierarchical(
            3,
            1,
            'PAK',
            layer_files,
            layer_cache
        )
        self.assertFalse(result)
        result = search_hierarchical(
            3,
            1,
            'AUT',
            layer_files,
            layer_cache
        )
        self.assertTrue(result)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_level_country(self):
        LayerFileF.create(
            layer_upload_session=self.upload_session,
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
            layer_upload_session=self.upload_session,
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
        has_valid_level = validate_level_country(
            self.upload_session,
            'AUT',
            3
        )
        self.assertFalse(has_valid_level)
        has_valid_level = validate_level_country(
            self.upload_session,
            'VCT',
            2
        )
        self.assertTrue(has_valid_level)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_retrieve_layer0_default_codes(self):
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
                        'id': self.idType.id
                    }
                }
            ],
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_0.geojson')
            )
        )
        read_layer_files_entity_temp(upload_session)
        result = retrieve_layer0_default_codes(upload_session, overwrite=True)
        self.assertEqual(len(result), 1)
        pak = [d for d in result if d['layer0_id'] == 'PAK']
        self.assertEqual(len(pak), 1)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_level_1(self):
        adm_user = UserF.create(
            username='test_user',
            is_superuser=True, is_staff=True
        )
        upload_session = LayerUploadSessionF.create(
            uploader=adm_user,
            dataset=self.dataset
        )
        # use different parent id field than level0 PCode
        layer_file_1 = LayerFileF.create(
            layer_upload_session=upload_session,
            level='1',
            parent_id_field='adm0_id',
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
                              'geojson_dataset', 'level_1_2.geojson')
            ),
            uploader=adm_user
        )
        layer_file_2 = LayerFileF.create(
            layer_upload_session=upload_session,
            level='2',
            location_type_field='type',
            parent_id_field='code_1',
            layer_file=(
                absolute_path('georepo', 'tests',
                              'geojson_dataset', 'level_2_2.geojson')
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
            uploader=adm_user
        )

        self.assertTrue(os.path.exists(layer_file_1.layer_file.path))
        self.assertTrue(os.path.exists(layer_file_2.layer_file.path))

        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=self.geographical_entity
        )
        read_layer_files_entity_temp(upload_session)
        # create EntityUploadChildLv1 for PAK003
        EntityUploadChildLv1F.create(
            entity_upload=entity_upload,
            entity_id='PAK003',
            entity_name='Khyber Pakhtunkhwa',
            feature_index=0
        )
        status = validate_layer_file(
            entity_upload=entity_upload
        )
        updated_entity_upload = EntityUploadStatus.objects.get(
            id=entity_upload.id
        )
        # if it is parent matching, then parent code validation is ignored
        self.assertTrue(status)
        self.assertTrue(updated_entity_upload.revised_geographical_entity)
        # expected result: all entities are being kept
        self.assertTrue(GeographicalEntity.objects.filter(
            layer_file=layer_file_1
        ).exists())
        self.assertTrue(GeographicalEntity.objects.filter(
            layer_file=layer_file_2
        ).exists())

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_level_admin_1(self):
        LayerFileF.create(
            layer_upload_session=self.upload_session,
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
            layer_upload_session=self.upload_session,
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
        has_valid_level = validate_level_admin_1(
            self.upload_session,
            ['PAK003'],
            1
        )
        self.assertTrue(has_valid_level)
        has_valid_level = validate_level_admin_1(
            self.upload_session,
            ['PAK003'],
            2
        )
        self.assertFalse(has_valid_level)
        has_valid_level = validate_level_admin_1(
            self.upload_session,
            ['PAK003', 'VCT-20210414-3', 'VCT-20210414-2'],
            2
        )
        self.assertTrue(has_valid_level)

    @mock.patch(
        'modules.admin_boundaries.qc_validation.GEOSGeometry.covers',
        mock.Mock(side_effect=mock_geom_covers))
    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_validate_geo_overlaps(self):
        dataset = DatasetF.create(
            module=self.module
        )
        upload_session = LayerUploadSessionF.create(
            dataset=dataset
        )
        test_file_path = (
            absolute_path(
                'georepo', 'tests',
                'geojson_dataset', 'damascus_qudsiya.geojson'
            )
        )
        LayerFileF.create(
            layer_upload_session=upload_session,
            level=1,
            parent_id_field='ADM0_PCODE',
            entity_type='Sub_district',
            name_fields=[
                {
                    'field': 'NAME_EN',
                    'default': True,
                    'selectedLanguage': self.language.id
                }
            ],
            id_fields=[
                {
                    'field': 'PCODE',
                    'default': True,
                    'idType': {
                        'id': self.idType.id,
                        'name': 'PCode'
                    }
                }
            ],
            layer_file=test_file_path
        )
        geographical_entity = GeographicalEntityF.create(
            dataset=dataset,
            level=0,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='SY',
            revision_number=1,
            geometry=self.geographical_entity.geometry
        )
        entity_upload = EntityUploadF.create(
            upload_session=upload_session,
            original_geographical_entity=geographical_entity
        )
        # when there is only overlaps error, the entities are not removed
        # update 2023-04-05: this case is not classified
        # as overlaps using new check
        status = validate_layer_file(
            entity_upload=entity_upload
        )
        self.assertTrue(status)

    @override_settings(MEDIA_ROOT='/home/web/django_project/georepo')
    def test_clear_pending_entities(self):
        status, layer_files, _, entity_upload = (
            self.do_validate_layer_from_level_0()
        )
        self.assertTrue(status)
        self.assertTrue(entity_upload.revised_geographical_entity)
        revised_entity = entity_upload.revised_geographical_entity
        entity_upload.revised_geographical_entity = None
        entity_upload.save(update_fields=['revised_geographical_entity'])
        revised_entity.delete_by_ancestor()
        layer_file = layer_files[0]
        layer_file_1 = layer_files[1]
        self.assertFalse(
            GeographicalEntity.objects.filter(
                internal_code='PAK',
                is_approved=None,
                layer_file_id=layer_file.id,
                admin_level_name='CountryF'
            ).exists()
        )
        self.assertFalse(
            GeographicalEntity.objects.filter(
                parent__internal_code='PAK',
                is_approved=None,
                layer_file_id=layer_file_1.id,
                admin_level_name='ProvinceF'
            ).exists()
        )
        self.assertEqual(
            EntityName.objects.count(), 0
        )
        self.assertEqual(
            EntityId.objects.count(), 0
        )


class FindEntityUploadTestCase(TransactionTestCase):

    def setUp(self) -> None:
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module
        )
        self.upload_session = LayerUploadSessionF.create(
            dataset=self.dataset,
            tolerance=1e-8,
            overlaps_threshold=0.01,
            gaps_threshold=0.01
        )

    def test_find_twice_one_after_another(self):
        entity_upload = EntityUploadF.create(
            original_geographical_entity=None,
            upload_session=self.upload_session,
            revised_entity_id='PAK',
            admin_level_names={
                '0': 'CountryF',
                '1': 'ProvinceF',
                '2': 'DistrictF'
            },
            status=STARTED
        )
        with transaction.atomic():
            upload = find_entity_upload(
                EntityUploadStatus.objects.filter(id=entity_upload.id),
                STARTED,
                PROCESSING,
                timezone.now()
            )
            self.assertTrue(upload)
        # lock should be released, but upload has been updated to PROCESSING
        with transaction.atomic():
            upload = find_entity_upload(
                EntityUploadStatus.objects.filter(id=entity_upload.id),
                STARTED,
                PROCESSING,
                timezone.now()
            )
            self.assertFalse(upload)

    def test_find_twice_parallel_return_none(self):
        entity_upload = EntityUploadF.create(
            original_geographical_entity=None,
            upload_session=self.upload_session,
            revised_entity_id='PAK',
            admin_level_names={
                '0': 'CountryF',
                '1': 'ProvinceF',
                '2': 'DistrictF'
            },
            status=STARTED
        )
        with transaction.atomic():
            upload = find_entity_upload(
                EntityUploadStatus.objects.filter(id=entity_upload.id),
                STARTED,
                PROCESSING,
                timezone.now()
            )
            self.assertTrue(upload)

            # the first tx not committed, lock should be still in effect
            with transaction.atomic():
                upload = find_entity_upload(
                    EntityUploadStatus.objects.filter(
                        id=entity_upload.id
                    ),
                    STARTED,
                    PROCESSING,
                    timezone.now()
                )
                self.assertFalse(upload)
