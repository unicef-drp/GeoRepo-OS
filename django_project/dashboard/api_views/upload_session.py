import math
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from azure_auth.backends import AzureAuthRequiredMixin

from dashboard.models.layer_upload_session import (
    LayerUploadSession,
    PENDING, DONE, CANCELED, ERROR,
    VALIDATING, REVIEWING,
    LayerUploadSessionActionLog
)
from dashboard.serializers.upload_session import (
    UploadSessionSerializer,
    DetailUploadSessionSerializer
)
from dashboard.models.entity_upload import (
    EntityUploadStatus, REVIEWING as UPLOAD_REVIEWING
)
from dashboard.serializers.dataset import (
    DatasetSerializer
)
from georepo.models import Dataset, GeographicalEntity
from georepo.utils.module_import import module_function
from dashboard.api_views.common import (
    DatasetReadPermission,
    DatasetWritePermission
)
from core.models.preferences import SitePreferences
from dashboard.tasks.upload import (
    delete_layer_upload_session,
    reset_upload_session
)


class AddUploadSession(AzureAuthRequiredMixin,
                       DatasetWritePermission, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def post(self, request, *args, **kwargs):
        source = request.data.get('source', '')
        description = request.data.get('description', '')

        dataset = Dataset.objects.get(
            id=kwargs.get('id')
        )
        # check if dataset is deprecated
        if not dataset.is_active:
            return Response(data={
                'detail': 'Unable to add data to deprecated dataset',
            }, status=400)
        # get default values for gaps, overlap, and tolerance
        params = SitePreferences.preferences().default_geometry_checker_params

        layer_session = LayerUploadSession.objects.create(
            uploader=self.request.user,
            status=PENDING,
            source=source,
            description=description,
            dataset=dataset,
            tolerance=params['tolerance'],
            overlaps_threshold=params['overlaps_threshold'],
            gaps_threshold=params['gaps_threshold'],
        )
        return Response(data={
            'session_id': layer_session.id,
        }, status=200)


class UpdateUploadSession(AzureAuthRequiredMixin, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def post(self, request, format=None):
        source = request.data.get('source', '')
        description = request.data.get('description', '')
        session = request.data.get('session', '')
        is_historical_upload = request.data.get('is_historical_upload', '')
        historical_start_date = request.data.get('historical_start_date', None)
        historical_end_date = request.data.get('historical_end_date', None)
        tolerance = request.data.get('tolerance', None)
        overlaps_threshold = request.data.get('overlaps_threshold', None)
        gaps_threshold = request.data.get('gaps_threshold', None)

        upload_session = LayerUploadSession.objects.get(
            id=session
        )
        if not upload_session.is_read_only():
            upload_session.source = source
            upload_session.description = description
            upload_session.is_historical_upload = is_historical_upload
            if is_historical_upload:
                upload_session.historical_start_date = historical_start_date
                upload_session.historical_end_date = historical_end_date
            else:
                upload_session.historical_start_date = None
                upload_session.historical_end_date = None
            if tolerance is not None:
                upload_session.tolerance = tolerance
            if overlaps_threshold is not None:
                upload_session.overlaps_threshold = overlaps_threshold
            if gaps_threshold is not None:
                upload_session.gaps_threshold = gaps_threshold
            upload_session.save()

        return Response(data={
            'session_id': upload_session.id,
        }, status=200)


class UploadSessionList(AzureAuthRequiredMixin, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def _filter_queryset(self, queryset, request):
        criteria_field_mapping = {
            'id': 'id',
            'uploaded_by': 'uploader__username',
            'type': 'dataset__module__name',
            'dataset': 'dataset__label',
            'status': 'status',
        }

        filter_kwargs = {}
        for filter_field, model_field in criteria_field_mapping.items():
            filter_values = dict(request.data).get(filter_field, [])
            if not filter_values:
                continue
            filter_kwargs.update({f'{model_field}__in': filter_values})

        if 'level_0_entity' in dict(request.data):
            filter_values = sorted(
                dict(request.data).get('level_0_entity', [])
            )
            if filter_values:
                entity_uploads = EntityUploadStatus.objects.filter(
                    revised_geographical_entity__label__in=filter_values
                ).values_list('upload_session')
                upload_sessions = LayerUploadSession.objects.filter(
                    Q(dataset__module__name__in=filter_values) |
                    Q(id__in=entity_uploads)
                )

                filter_kwargs.update({'id__in': upload_sessions})

        return queryset.filter(**filter_kwargs)

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        char_fields = [
            field.name for field in LayerUploadSession._meta.get_fields() if
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

        ordering_mapping = {
            'id': 'id',
            'uploaded_by': 'uploader__username',
            'type': 'dataset__module__name',
            'dataset': 'dataset__label',
            'status': 'status',
        }
        sort_by = ordering_mapping.get(sort_by, sort_by)
        ordering = sort_by if sort_direction == 'asc' else f"-{sort_by}"
        queryset = queryset.order_by(ordering)
        return queryset

    def post(self, request):
        status = request.GET.get('status', '')
        layer_sessions = LayerUploadSession.\
            get_upload_session_for_user(request.user)
        if status:
            layer_sessions = layer_sessions.filter(
                status__iexact=status
            )
        layer_sessions = self._search_queryset(
            layer_sessions, self.request
        )
        layer_sessions = self._filter_queryset(
            layer_sessions, self.request
        )
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.query_params.get('page_size', '10'))
        layer_sessions = self._sort_queryset(layer_sessions, self.request)
        paginator = Paginator(layer_sessions, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = UploadSessionSerializer(
                paginated_entities,
                many=True
            ).data
        output = output
        return Response({
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output,
        })


class UploadSessionFilterValue(
    AzureAuthRequiredMixin,
    APIView
):
    """
    Get filter value for given UploadSession and criteria
    """
    permission_classes = [IsAuthenticated]
    querysets = LayerUploadSession.objects.none()

    def fetch_criteria_values(self, criteria):
        criteria_field_mapping = {
            'id': 'id',
            'uploaded_by': 'uploader__username',
            'type': 'dataset__module__name',
            'dataset': 'dataset__label',
            'status': 'status',
        }
        field = criteria_field_mapping.get(criteria, None)

        if not field:
            if criteria == 'level_0_entity':
                return self.fetch_level_0_entity()

        filter_values = self.querysets.\
            filter(**{f"{field}__isnull": False}).order_by().\
            values_list(field, flat=True).distinct()
        return [val for val in filter_values]

    def fetch_level_0_entity(self):
        return list(EntityUploadStatus.objects.
                    filter(revised_geographical_entity__label__isnull=False).
                    order_by('revised_geographical_entity__label').
                    values_list(
                        'revised_geographical_entity__label', flat=True
                    ).
                    distinct())

    def get(self, request, criteria, *args, **kwargs):
        self.querysets = LayerUploadSession.\
            get_upload_session_for_user(request.user)
        try:
            data = self.fetch_criteria_values(criteria)
        except AttributeError:
            data = []
        return Response(status=200, data=data)


class UploadSessionDetail(AzureAuthRequiredMixin, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def get(self, request, *args, **kwargs):
        upload_session_id = kwargs.get('id')
        upload_session = get_object_or_404(
            LayerUploadSession,
            id=upload_session_id
        )
        return Response(
            DetailUploadSessionSerializer(upload_session).data
        )


class UploadSessionUpdateStep(AzureAuthRequiredMixin, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def post(self, request, *args, **kwargs):
        upload_session_id = request.data.get('id')
        step = request.data.get('step')
        upload_session = get_object_or_404(
            LayerUploadSession,
            id=upload_session_id
        )
        session_state = upload_session.session_state()
        check_can_update_step = module_function(
            upload_session.dataset.module.code_name,
            'config',
            'check_can_update_step')
        can_update = (
            check_can_update_step(upload_session, step, session_state)
        )
        ongoing_step = -1
        if can_update:
            upload_session.last_step = step
            upload_session.save(update_fields=['last_step'])
            last_step = step
        else:
            last_step = upload_session.last_step
        get_ongoing_step = module_function(
            upload_session.dataset.module.code_name,
            'config',
            'check_ongoing_step')
        ongoing_step = get_ongoing_step(upload_session, session_state)
        dataset_name = upload_session.dataset.label
        module_name = upload_session.dataset.module.name
        # return dataset name
        return Response(
            status=200,
            data={
                'dataset_name': dataset_name,
                'type': module_name,
                'last_step': last_step,
                'ongoing_step': ongoing_step,
                'is_read_only': upload_session.is_read_only(),
                'status': upload_session.status,
                'is_in_progress': upload_session.is_in_progress(),
                'has_any_result': upload_session.has_any_result()
            }
        )


class UploadSessionSummary(AzureAuthRequiredMixin, APIView):
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def get(self, request, pk, *args, **kwargs):
        upload_session_id = pk
        upload_session = get_object_or_404(
            LayerUploadSession,
            id=upload_session_id
        )
        dataset = upload_session.dataset
        layer_files = upload_session.layerfile_set.all().order_by(
            'level'
        )
        summaries = []
        for layer_file in layer_files:
            get_summary = module_function(
                dataset.module.code_name,
                'field_mapping',
                'get_summary')
            summaries.append(get_summary(layer_file))

        return Response(
            status=200,
            data={
                'is_read_only': upload_session.is_read_only(),
                'summaries': summaries
            }
        )


class CanAddUpload(AzureAuthRequiredMixin, DatasetReadPermission, APIView):
    """
    Api view to check whether user can upload a new data or not
    If there is level 0 upload, then block any other upload
    else can still upload admin level 1 when there is country
    without any upload in state = [REVIEWING]
    active_upload = return current user's upload
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        dataset = get_object_or_404(
            Dataset,
            id=kwargs.get('id')
        )
        # check if dataset is deprecated
        if not dataset.is_active:
            result = {
                'can_upload': False,
                'dataset': (
                    DatasetSerializer(
                        dataset,
                        many=False,
                        context={
                            'user': request.user
                        }
                    ).data
                )
            }
            return Response(result)
        has_permission_to_upload = self.can_add_upload(dataset)
        if not has_permission_to_upload:
            result = {
                'can_upload': False,
                'dataset': (
                    DatasetSerializer(
                        dataset,
                        many=False,
                        context={
                            'user': request.user
                        }
                    ).data
                )
            }
            return Response(result)
        active_upload = LayerUploadSession.objects.filter(
            dataset_id=dataset.id
        ).exclude(
            status__in=[DONE, ERROR, CANCELED]
        )
        can_upload = not active_upload.exists()
        if can_upload:
            result = {
                'can_upload': can_upload,
                'dataset': (
                    DatasetSerializer(
                        dataset,
                        many=False,
                        context={
                            'user': request.user
                        }
                    ).data
                )
            }
            return Response(result)
        active_upload_ids = active_upload.values('id')
        # check whether there is level 0 upload
        upload_level0 = EntityUploadStatus.objects.filter(
            upload_session__in=active_upload_ids,
            original_geographical_entity__isnull=True
        ).exclude(
            revised_entity_id__exact=''
        )
        if upload_level0.exists():
            result = {
                'can_upload': can_upload,
                'dataset': (
                    DatasetSerializer(
                        dataset,
                        many=False,
                        context={
                            'user': request.user
                        }
                    ).data
                )
            }
            active_upload0 = upload_level0.filter(
                upload_session__uploader=request.user
            ).last()
            if active_upload0:
                result['active_upload'] = (
                    UploadSessionSerializer(
                        active_upload0.upload_session,
                        many=False
                    ).data
                )
            return Response(result)
        # check whether there is available country
        upload_adminlevel1 = EntityUploadStatus.objects.filter(
            upload_session__in=active_upload_ids,
            original_geographical_entity__isnull=False,
            status__in=[UPLOAD_REVIEWING]
        ).order_by('original_geographical_entity')
        available_country = GeographicalEntity.objects.filter(
            dataset_id=dataset.id,
            level=0,
            is_approved=True,
            is_latest=True
        ).exclude(
            id__in=upload_adminlevel1.values_list(
                'original_geographical_entity',
                flat=True
            ).distinct()
        )
        result = {
            'can_upload': available_country.exists(),
            'dataset': (
                DatasetSerializer(
                    dataset,
                    many=False,
                    context={
                        'user': request.user
                    }
                ).data
            )
        }
        active_upload1 = upload_adminlevel1.filter(
            upload_session__uploader=request.user
        ).last()
        if active_upload1:
            result['active_upload'] = (
                UploadSessionSerializer(
                    active_upload1.upload_session,
                    many=False
                ).data
            )
        elif active_upload.exists():
            active_upload = active_upload.filter(
                uploader=request.user
            ).first()
            if active_upload:
                # find other pending session
                result['active_upload'] = (
                    UploadSessionSerializer(
                        active_upload,
                        many=False
                    ).data
                )
        return Response(result)


class DeleteUploadSession(AzureAuthRequiredMixin,
                          UserPassesTestMixin, APIView):
    """
    API view to delete Upload Session that is in statuses:
    PENDING, CANCELED, ERROR, VALIDATING, REVIEWING
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )

    STATUSES = [
        PENDING, CANCELED, ERROR, VALIDATING, REVIEWING
    ]

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        upload_session = LayerUploadSession.objects.get(
            id=self.kwargs.get('id'))
        if upload_session.uploader == self.request.user:
            return True
        return False

    def post(self, request, *args, **kwargs):
        upload_session = LayerUploadSession.objects.get(
            id=kwargs.get('id')
        )
        if upload_session.status not in self.STATUSES:
            return Response(
                status=400,
                data={
                    'detail': (
                        'Cannot delete the upload '
                        f'with status {upload_session.status}'
                    )
                }
            )
        task = delete_layer_upload_session.delay(upload_session.id)
        return Response(
            status=200,
            data={
                'task_id': task.id
            }
        )


class ResetUploadSession(AzureAuthRequiredMixin,
                         UserPassesTestMixin, APIView):
    """
    Reset upload session progress
    """
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        upload_session = LayerUploadSession.objects.get(
            id=self.kwargs.get('id'))
        if upload_session.uploader == self.request.user:
            return True
        return False

    def post(self, request, *args, **kwargs):
        upload_session = LayerUploadSession.objects.get(
            id=kwargs.get('id')
        )
        if upload_session.is_read_only():
            return Response(status=200)
        step = int(kwargs.get('step'))
        reset_last_step = (
            request.GET.get('cancel', 'false') == 'true'
        )
        if reset_last_step:
            step = upload_session.last_step
        # check if it has passed qc_validation
        existing_uploads = upload_session.entityuploadstatus_set.exclude(
            status=''
        )
        preprocessing = False
        qc_validation = False
        if existing_uploads.exists():
            qc_validation = True
            if step < 3:
                preprocessing = True
        else:
            preprocessing = True
        task = reset_upload_session.delay(
            upload_session.id, preprocessing, qc_validation, reset_last_step)
        if reset_last_step:
            # set the status to cancel
            upload_session.status = CANCELED
            upload_session.save(update_fields=['status'])
        return Response(
            status=200,
            data={
                'task_id': task.id
            }
        )


class CheckUploadSessionActionStatus(AzureAuthRequiredMixin,
                                     UserPassesTestMixin, APIView):
    """Check action status."""
    permission_classes = (
        permissions.IsAuthenticated,
    )

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        upload_session = LayerUploadSession.objects.get(
            id=self.kwargs.get('id'))
        if upload_session.uploader == self.request.user:
            return True
        return False

    def get(self, request, *args, **kwargs):
        upload_session = get_object_or_404(
            LayerUploadSession, id=kwargs.get('id')
        )
        action_uuid = request.GET.get('action', '')
        action = LayerUploadSessionActionLog.objects.filter(
            session=upload_session,
            uuid=action_uuid
        ).first()
        return Response(
            status=200,
            data={
                'has_action': action is not None,
                'status': action.status if action else 'None',
                'result': action.result if action else None
            }
        )
