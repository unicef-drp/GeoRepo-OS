import mock
from django.test import TestCase
from django.db.models import Q
from georepo.models import (
    GeographicalEntity, DatasetView
)
from georepo.tests.model_factories import (
    UserF, DatasetF, GeographicalEntityF, ModuleF
)
from dashboard.models import (
    LayerUploadSession,
    REVIEWING, EntityUploadStatus,
    APPROVED
)
from dashboard.models.batch_review import (
    BatchReview, PENDING, DONE
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF, \
    EntityUploadF, BoundaryComparisonF
from dashboard.tasks.review import process_batch_review


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_run_generate_vector_tiles(*args, **kwargs):
    return DummyTask('1')


class TestReviewApproval(TestCase):

    def setUp(self) -> None:
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=False
        )
        self.superuser = UserF.create(is_superuser=True)

    @mock.patch(
        'dashboard.tasks.review.trigger_generate_dynamic_views'
    )
    @mock.patch(
        'dashboard.tasks.review.check_affected_dataset_views'
    )
    def test_batch_approval(self, mock_check_views, mocked_dynamic_views):
        # create upload_session + entity_upload
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
            status=REVIEWING,
            comparison_data_ready=True
        )
        mocked_dynamic_views.side_effect = mocked_run_generate_vector_tiles
        # create batch review
        batch_review = BatchReview.objects.create(
            review_by=self.superuser,
            is_approve=True,
            status=PENDING,
            upload_ids=[entity_upload.id]
        )
        # call batch processing
        process_batch_review(batch_review.id)
        # assert batch review
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
            2
        )
        # check dynamic views have been refreshed
        mocked_dynamic_views.assert_called()
        # check affected view is checked
        mock_check_views.assert_called()
        # check concept ucode have been generated
        self.assertFalse(
            GeographicalEntity.objects.filter(
                id__in=geo_new.all_children(),
            ).filter(
                Q(concept_ucode__isnull=True) | Q(concept_ucode='')
            ).exists()
        )
        # check updated batch_review
        updated_batch_review = BatchReview.objects.get(id=batch_review.id)
        self.assertEqual(updated_batch_review.status, DONE)
        self.assertEqual(len(updated_batch_review.processed_ids), 1)
