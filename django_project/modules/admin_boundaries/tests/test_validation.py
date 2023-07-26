from django.test import TestCase
from georepo.tests.model_factories import (
    DatasetF, UserF, ModuleF
)
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    EntityUploadF
)
from modules.admin_boundaries.qc_validation import (
    is_validation_result_importable
)
from dashboard.models.entity_upload import (
    ERROR
)


class IsUploadImportableTestCase(TestCase):

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
        self.user_a = UserF.create()
        self.superuser = UserF.create(
            is_superuser=True
        )

    def test_is_upload_importable(self):
        # entity upload without warning
        entity_upload_1 = EntityUploadF.create(
            original_geographical_entity=None,
            upload_session=self.upload_session,
            revised_entity_id='PAK',
            admin_level_names={
                '0': 'CountryF',
                '1': 'ProvinceF',
                '2': 'DistrictF'
            },
            status=ERROR,
            summaries=[
                {
                    "Level": 0,
                    "Entity": "Angola",
                    "Gaps": 0,
                    "Overlaps": 2,
                    "Self Contacts": 0,
                    "Parent Missing": 0,
                    "Duplicate Nodes": 5,
                    "Self Intersects": 0,
                    "Duplicated Codes": 0,
                    "Not Within Parent": 0,
                    "Parent Code Missing": 0,
                    "Default Code Missing": 0,
                    "Default Name Missing": 0,
                    "Duplicated Geometries": 1,
                    "Invalid Privacy Level": 0,
                    "Privacy Level Missing": 0,
                    "Upgraded Privacy Level": 0,
                    "Feature within other features": 2,
                    "Polygon with less than 4 nodes": 0
                }
            ]
        )
        # check with user_a
        is_importable, is_warning = is_validation_result_importable(
            entity_upload_1, self.user_a
        )
        self.assertFalse(is_importable)
        self.assertFalse(is_warning)
        # check with superuser
        is_importable, is_warning = is_validation_result_importable(
            entity_upload_1, self.superuser
        )
        self.assertTrue(is_importable)
        self.assertFalse(is_warning)
        # entity upload with warning only
        entity_upload_2 = EntityUploadF.create(
            original_geographical_entity=None,
            upload_session=self.upload_session,
            revised_entity_id='PAK',
            admin_level_names={
                '0': 'CountryF',
                '1': 'ProvinceF',
                '2': 'DistrictF'
            },
            status=ERROR,
            summaries=[
                {
                    "Level": 0,
                    "Entity": "Angola",
                    "Gaps": 0,
                    "Overlaps": 0,
                    "Self Contacts": 0,
                    "Parent Missing": 0,
                    "Duplicate Nodes": 5,
                    "Self Intersects": 1,
                    "Duplicated Codes": 0,
                    "Not Within Parent": 0,
                    "Parent Code Missing": 0,
                    "Default Code Missing": 0,
                    "Default Name Missing": 0,
                    "Duplicated Geometries": 0,
                    "Invalid Privacy Level": 0,
                    "Privacy Level Missing": 0,
                    "Upgraded Privacy Level": 2,
                    "Feature within other features": 0,
                    "Polygon with less than 4 nodes": 0
                }
            ]
        )
        # check with user_a
        is_importable, is_warning = is_validation_result_importable(
            entity_upload_2, self.user_a
        )
        self.assertTrue(is_importable)
        self.assertTrue(is_warning)
        # check with superuser
        is_importable, is_warning = is_validation_result_importable(
            entity_upload_2, self.superuser
        )
        self.assertTrue(is_importable)
        self.assertTrue(is_warning)
