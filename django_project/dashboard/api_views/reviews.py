import math

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.api_views.common import (
    DatasetWritePermission
)
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
    APPROVED,
    REJECTED
)
from dashboard.serializers.entity_upload import EntityUploadSerializer
from dashboard.tasks import run_comparison_boundary
from dashboard.tasks.review import (
    review_approval,
    process_batch_review
)
from georepo.utils.module_import import module_function


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

    def _filter_queryset(self, queryset, request):
        criteria_field_mapping = {
            'level_0_entity': 'revised_geographical_entity__label',
            'upload': 'upload_session__source',
            'revision': 'revised_geographical_entity__revision_number',
            'dataset': 'upload_session__dataset__label'
        }

        filter_kwargs = {}
        for filter_field, model_field in criteria_field_mapping.items():
            filter_values = dict(request.data).get(filter_field, [])
            if not filter_values:
                continue
            filter_kwargs.update({f'{model_field}__in': filter_values})

        if 'status' in dict(request.data):
            filter_values = sorted(dict(request.data).get('status', []))
            if not filter_values or \
                filter_values == [APPROVED, 'Pending', REJECTED]:
                return queryset.filter(**filter_kwargs)

            non_pending_filter_combinations = [
                [APPROVED],
                [REJECTED],
                [APPROVED, REJECTED]
            ]
            pending_status = [
                choice[0] for choice in EntityUploadStatus.STATUS_CHOICES if
                choice[0] not in [APPROVED, REJECTED]
            ]
            if filter_values in non_pending_filter_combinations:
                filter_kwargs.update({'status__in': filter_values})
            elif 'Pending' in filter_values:
                if APPROVED in filter_values:
                    filter_kwargs.update(
                        {
                            'status__in': [
                                *pending_status, APPROVED
                            ]
                        }
                    )
                elif REJECTED in filter_values:
                    filter_kwargs.update(
                        {
                            'status__in': [
                                *pending_status, REJECTED
                            ]
                        }
                    )
                else:
                    filter_kwargs.update({'status__in': [pending_status]})

        return queryset.filter(**filter_kwargs)

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        char_fields = [
            field.name for field in EntityUploadStatus._meta.get_fields() if
            field.get_internal_type() in
            ['UUIDField', 'CharField', 'TextField']
        ]
        q_args = [
            Q(**{f"{field}__icontains": search_text}) for field in char_fields
        ]
        args = Q()
        for arg in q_args:
            args |= arg
        queryset = queryset.filter(*(args,))
        return queryset

    def _sort_queryset(self, queryset, request):
        sort_by = request.query_params.get('sort_by', 'id')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        if not sort_by:
            sort_by = 'id'
        if not sort_direction:
            sort_direction = 'asc'
        ordering = sort_by if sort_direction == 'asc' else f"-{sort_by}"
        queryset = queryset.order_by(ordering)
        return queryset

    def post(self, request, *args, **kwargs):
        review_querysets = EntityUploadStatus.get_user_entity_upload_status(
            request.user
        )
        review_querysets = self._search_queryset(
            review_querysets, self.request
        )
        review_querysets = self._filter_queryset(
            review_querysets, self.request
        )
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.query_params.get('page_size', '10'))
        review_querysets = self._sort_queryset(review_querysets, self.request)
        paginator = Paginator(review_querysets, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = EntityUploadSerializer(
                paginated_entities,
                many=True
            ).data
        return Response({
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output,
        })


class ReviewFilterValue(
    AzureAuthRequiredMixin,
    APIView
):
    """
    Get filter value for given Review and criteria
    """
    permission_classes = [IsAuthenticated]
    review_querysets = EntityUploadStatus.objects.none()

    def fetch_criteria_values(self, criteria):
        criteria_field_mapping = {
            'level_0_entity': 'revised_geographical_entity__label',
            'upload': 'upload_session__source',
            'revision': 'revised_geographical_entity__revision_number',
        }
        field = criteria_field_mapping.get(criteria, None)

        if not field:
            if criteria == 'dataset':
                return self.fetch_dataset()
            return self.fetch_status()

        filter_values = self.reviews_querysets.\
            filter(**{f"{field}__isnull": False}).order_by().\
            values_list(field, flat=True).distinct()
        return [val for val in filter_values]

    def fetch_dataset(self):
        return list(self.reviews_querysets.filter(
            upload_session__dataset__label__isnull=False
        ).exclude(
            upload_session__dataset__label__exact=''
        ).order_by().values_list(
            'upload_session__dataset__label', flat=True
        ).distinct())

    def fetch_status(self):
        return [
            APPROVED,
            REJECTED,
            'Pending'
        ]

    def get(self, request, criteria, *args, **kwargs):
        self.reviews_querysets = \
            EntityUploadStatus.get_user_entity_upload_status(request.user)
        try:
            data = self.fetch_criteria_values(criteria)
        except AttributeError:
            data = []
        return Response(status=200, data=data)


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
