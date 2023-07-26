
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.models.dataset import Dataset
from georepo.utils.permission import get_dataset_to_review
from dashboard.models import (
    EntityUploadStatus, LayerUploadSession,
    REVIEWING
)
from dashboard.models.batch_review import (
    BatchReview, PENDING, PROCESSING
)
from dashboard.models.entity_upload import (
    REVIEWING as UPLOAD_REVIEWING,
    PROCESSING_APPROVAL,
    APPROVED
)
from dashboard.serializers.entity_upload import EntityUploadSerializer
from dashboard.tasks import run_comparison_boundary
from georepo.utils.module_import import module_function
from dashboard.api_views.common import (
    DatasetWritePermission
)
from dashboard.tasks.review import (
    review_approval,
    process_batch_review
)


class ReadyToReview(AzureAuthRequiredMixin, APIView):
    """Api to update upload session to ready to review"""
    permission_classes = [IsAuthenticated]

    def validate_selected_country(self, dataset, user, uploads):
        is_importable_func = module_function(
            dataset.module.code_name,
            'qc_validation',
            'is_validation_result_importable'
        )
        for entity_upload in uploads:
            upload_session = entity_upload.upload_session
            if entity_upload.original_geographical_entity:
                country = entity_upload.original_geographical_entity.label
                other_uploads = EntityUploadStatus.objects.filter(
                    original_geographical_entity=(
                        entity_upload.original_geographical_entity
                    ),
                    upload_session__dataset=upload_session.dataset,
                    status=UPLOAD_REVIEWING
                ).exclude(
                    upload_session=upload_session
                )
                if other_uploads.exists():
                    return False, f'{country} has upload being reviewed'
            else:
                country = entity_upload.revised_entity_name
            is_importable, _ = is_importable_func(
                entity_upload,
                user
            )
            if not is_importable:
                return False, (
                    f'{country} cannot be imported because '
                    'there is validation error!'
                )
        return True, ''

    def post(self, request, *args, **kwargs):
        upload_entity_ids = request.data.get('upload_entities').split(',')
        uploads = EntityUploadStatus.objects.filter(
            id__in=upload_entity_ids
        )
        if uploads.count() == 0:
            return Response(
                status=400,
                data={
                    'detail': 'Empty Entity Uploads'
                }
            )
        upload_session = LayerUploadSession.objects.filter(
            id__in=uploads.values('upload_session')
        )
        # validate upload_session is not read only
        for session in upload_session:
            if session.is_read_only():
                return Response(
                    status=400,
                    data={
                        'detail': 'Invalid Upload Session'
                    }
                )
        upload_session_obj = upload_session.first()
        dataset = upload_session_obj.dataset
        # validate the imported countries has not in-review in other session
        is_selected_valid, error = self.validate_selected_country(
            dataset, request.user, uploads)
        if not is_selected_valid:
            return Response(status=400, data={
                        'detail': error
                    })
        ready_to_review_func = module_function(
            dataset.module.code_name,
            'prepare_review',
            'ready_to_review')
        ready_to_review_func(uploads)
        for upload in uploads:
            # Start the comparison boundary in the background
            run_comparison_boundary.apply_async(
                (upload.id,),
                queue='validation'
            )

        upload_session.update(status=REVIEWING)
        # remove entities from non-selected country
        non_selected_uploads = EntityUploadStatus.objects.filter(
            upload_session__in=upload_session
        ).exclude(
            id__in=upload_entity_ids
        )
        for upload in non_selected_uploads:
            if upload.revised_geographical_entity:
                revised = upload.revised_geographical_entity
                upload.revised_geographical_entity = None
                upload.save(update_fields=['revised_geographical_entity'])
                if revised:
                    revised.delete()
        return Response(status=200, data={
            'session_source': upload_session_obj.source
        })


class ReviewList(AzureAuthRequiredMixin, APIView):
    """Api to list all ready to review uploads"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        datasets = Dataset.objects.all().order_by('created_at')
        datasets = get_dataset_to_review(
            self.request.user,
            datasets
        )
        entity_uploads = EntityUploadStatus.objects.filter(
            status__in=[REVIEWING, APPROVED],
            upload_session__dataset__in=datasets
        ).order_by('-started_at')
        if not self.request.user.is_superuser:
            entity_uploads = entity_uploads.exclude(
                upload_session__uploader=self.request.user
            )
        return Response(
            EntityUploadSerializer(entity_uploads, many=True).data
        )


class ApproveRevision(AzureAuthRequiredMixin,
                      DatasetWritePermission, APIView):
    """Api for approval request of new revision"""
    permission_classes = [IsAuthenticated]

    def post(self, *args, **kwargs):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=self.request.data.get(
                'entity_upload_id')
        )
        upload_session = entity_upload.upload_session
        if not self.request.user.is_superuser:
            if self.request.user.id == upload_session.uploader.id:
                raise PermissionDenied(
                    'You are not allowed to do this action!'
                )
        task = review_approval.delay(entity_upload.id, self.request.user.id)
        entity_upload.task_id = task.id
        entity_upload.status = PROCESSING_APPROVAL
        entity_upload.save(update_fields=['task_id', 'status'])

        return Response(status=200)


class RejectRevision(AzureAuthRequiredMixin,
                     DatasetWritePermission, APIView):
    """Api for new revision rejection request"""
    permission_classes = [IsAuthenticated]

    def post(self, *args, **kwargs):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=self.request.data.get(
                'entity_upload_id')
        )
        upload_session = entity_upload.upload_session
        if not self.request.user.is_superuser:
            if self.request.user.id == upload_session.uploader.id:
                raise PermissionDenied(
                    'You are not allowed to do this action!'
                )
        dataset = entity_upload.upload_session.dataset
        reject_revision = module_function(
            dataset.module.code_name,
            'review',
            'reject_revision'
        )
        reject_revision(entity_upload)

        return Response(status=200)


class BatchReviewAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve status of batch review."""
        batch_review_id = int(kwargs.get('review_id', '0'))
        batch_review = None
        if batch_review_id == 0:
            # retrieve any pending/processing batch_review
            batch_review = BatchReview.objects.filter(
                review_by=request.user,
                status__in=[PENDING, PROCESSING]
            ).order_by('submitted_at').first()
        else:
            batch_review = get_object_or_404(
                BatchReview,
                id=batch_review_id
            )
        if batch_review:
            data = {
                'id': batch_review.id,
                'submitted_by': (
                    batch_review.review_by.username if
                    batch_review.review_by else ''
                ),
                'submitted_at': batch_review.submitted_at,
                'is_approve': batch_review.is_approve,
                'progress': batch_review.progress,
                'status': batch_review.status
            }
        else:
            data = {
                'id': 0,
                'submitted_by': '',
                'submitted_at': None,
                'is_approve': False,
                'progress': '',
                'status': ''
            }
        return Response(status=200, data=data)

    def post(self, request, *args, **kwargs):
        """Submit batch review."""
        upload_entity_ids = request.data.get('upload_entities')
        # TODO: check permisson from each dataset inside the uploads
        upload_ids = [int(upload_id) for upload_id in upload_entity_ids]
        batch_review = BatchReview.objects.create(
            review_by=request.user,
            is_approve=request.data.get('is_approve'),
            status=PENDING,
            upload_ids=upload_ids
        )
        # start worker task
        task = process_batch_review.delay(batch_review.id)
        batch_review.task_id = task.id
        batch_review.save(update_fields=['task_id'])
        return Response(status=200, data={
            'review_id': batch_review.id
        })


class PendingBatchReviewUploads(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve list of upload ids in pending/processing batch."""
        reviews = BatchReview.objects.filter(
            status__in=[PENDING, PROCESSING]
        )
        pending_reviews = set()
        for review in reviews:
            pending_reviews.update(review.upload_ids)
        return Response(pending_reviews)
