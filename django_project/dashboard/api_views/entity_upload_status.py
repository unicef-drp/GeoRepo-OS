import json
import math
from pytz import timezone
from collections import OrderedDict
from django.conf import settings
from django.db import connection
from django.db.models import Case, When, Value, Q, Count
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone as django_tz
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from azure_auth.backends import AzureAuthRequiredMixin
from georepo.models.entity import GeographicalEntity
from georepo.models.dataset import DatasetAdminLevelName
from dashboard.models import LayerUploadSession, EntityUploadStatus, \
    EntityUploadChildLv1, STARTED, PROCESSING, PROCESSING_ERROR, \
    EntityUploadStatusLog, IMPORTABLE_UPLOAD_STATUS_LIST
from dashboard.serializers.upload_session import DetailUploadSessionSerializer
from georepo.utils.module_import import module_function
from dashboard.api_views.common import EntityUploadStatusReadPermission
from georepo.utils.celery_helper import cancel_task
from georepo.tasks import validate_ready_uploads


class EntityUploadStatusDetail(AzureAuthRequiredMixin,
                               EntityUploadStatusReadPermission, APIView):
    """
    Get detail of entity upload status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=id
        )
        upload_session_data = DetailUploadSessionSerializer(
            entity_upload.upload_session,
            many=False,
            context={
                'max_level': entity_upload.max_level,
                'revised_entity': entity_upload.revised_geographical_entity,
                'revision_number': entity_upload.revision_number
            }
        ).data
        upload_session_data['comparison_ready'] = (
            entity_upload.comparison_data_ready is not None and
            entity_upload.comparison_data_ready is True
        )
        upload_session_data['upload_status'] = entity_upload.status
        upload_session_data['progress'] = entity_upload.progress
        upload_session_data['adm0_entity'] = (
            entity_upload.revised_geographical_entity.label if
            entity_upload.revised_geographical_entity else
            entity_upload.revised_entity_name
        )
        return Response(upload_session_data)


class EntityUploadStatusMetadata(AzureAuthRequiredMixin, APIView):
    """API to fetch all upload IDs and country names"""

    def get(self, request, *args, **kwargs):
        select_all = request.GET.get('select_all', 'false') == 'true'
        upload_session_id = request.GET.get('id', None)
        upload_session = LayerUploadSession.objects.get(
            id=upload_session_id
        )
        entity_uploads = (
            EntityUploadStatus.objects.select_related(
                'revised_geographical_entity',
                'original_geographical_entity'
            ).filter(
                upload_session=upload_session
            )
        )
        entity_uploads = entity_uploads.exclude(
            status=''
        )
        # is_all_finished should check to all uploads without pagination
        is_all_finished = not entity_uploads.filter(
            status__in=[STARTED, PROCESSING]
        ).exists()
        level_name_0 = DatasetAdminLevelName.objects.filter(
            dataset=upload_session.dataset,
            level=0
        ).first()
        return_ids = (
            select_all or is_all_finished or upload_session.is_read_only()
        )
        if return_ids:
            # filter ids that are importable
            case_list = [
                When(
                    status__in=IMPORTABLE_UPLOAD_STATUS_LIST,
                    then=Value(True)
                ),
                When(
                    Q(allowable_errors__gt=0) & Q(blocking_errors=0),
                    then=Value(True)
                )
            ]
            if request.user.is_superuser:
                case_list.append(
                    When(
                        Q(superadmin_bypass_errors__gt=0) &
                        Q(superadmin_blocking_errors=0),
                        then=Value(True)
                    )
                )
            is_importable = Case(
                *case_list,
                default=Value(False)
            )
            entity_uploads = entity_uploads.annotate(
                is_importable=is_importable
            ).filter(is_importable=True)
        return Response(
            status=200,
            data={
                'ids': (
                    entity_uploads.values_list('id', flat=True) if
                    return_ids else []
                ),
                'countries': [],
                'is_all_finished': is_all_finished,
                'level_name_0': (
                    level_name_0.label if level_name_0 else 'Country'
                ),
                'is_read_only': upload_session.is_read_only(),
            }
        )


class EntityUploadStatusList(AzureAuthRequiredMixin, APIView):

    def sort_error_summaries(self, summaries):
        if not summaries:
            return summaries
        result = []
        for summary in summaries:
            sorted = OrderedDict()
            if 'Level' in summary.keys():
                sorted['Level'] = summary['Level']
            if 'Entity' in summary.keys():
                sorted['Entity'] = summary['Entity']
            for key in summary.keys():
                if key not in ['Level', 'Entity']:
                    sorted[key] = summary[key]
            result.append(sorted)
        return result

    def get_status(self, status):
        if status == STARTED:
            return 'Queued'
        return status

    def _filter_status(self, request):
        status_list = request.data.get('status', [])
        if not status_list:
            return {}
        filter = []
        for status in status_list:
            if status == 'Not Completed':
                filter.append(STARTED)
                filter.append(PROCESSING)
            elif status == 'Queued':
                filter.append(STARTED)
            else:
                filter.append(status)
        return {
            'status__in': filter
        }

    def _filter_country(self, queryset, request):
        countries = request.data.get('countries', [])
        if not countries:
            return queryset
        return queryset.filter(
            Q(revised_geographical_entity__label__in=countries) |
            Q(original_geographical_entity__label__in=countries) |
            Q(revised_entity_name__in=countries)
        )

    def _filter_queryset(self, queryset, request):
        filter_kwargs = {}
        filter_kwargs.update(self._filter_status(request))
        queryset = queryset.filter(**filter_kwargs)
        return self._filter_country(queryset, request)

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        return queryset.filter(
            Q(revised_entity_name__icontains=search_text) |
            Q(revised_geographical_entity__label__icontains=search_text) |
            Q(original_geographical_entity__label__icontains=search_text)
        )

    def _get_job_summaries(self, queryset):
        job_summary_qs = queryset.values(
            'status'
        ).annotate(total=Count('status'))
        result = {}
        for value in job_summary_qs:
            result[self.get_status(value['status'])] = value['total']
        return result

    def post(self, request, *args, **kwargs):
        upload_session_id = request.GET.get('id', None)
        upload_session = LayerUploadSession.objects.get(
            id=upload_session_id
        )
        dataset = upload_session.dataset
        entity_uploads = (
            EntityUploadStatus.objects.select_related(
                'revised_geographical_entity',
                'original_geographical_entity'
            ).filter(
                upload_session=upload_session
            )
        )
        entity_uploads = entity_uploads.exclude(
            status=''
        )
        # count job summaries
        job_summaries = self._get_job_summaries(entity_uploads)
        # is_all_finished should check to all uploads without pagination
        is_all_finished = not entity_uploads.filter(
            status__in=[STARTED, PROCESSING]
        ).exists()
        # apply search and filter
        entity_uploads = self._search_queryset(entity_uploads, request)
        entity_uploads = self._filter_queryset(entity_uploads, request)
        # annotate priority status for sorting
        status_priority = Case(
            When(status=PROCESSING, then=Value(1)),
            default=Value(2),
        )
        entity_uploads = entity_uploads.annotate(
            status_priority=status_priority
        ).order_by('status_priority', 'id')
        # apply pagination
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.GET.get('page_size', '10'))
        paginator = Paginator(entity_uploads, page_size)
        total_page = math.ceil(paginator.count / page_size)
        total_count = paginator.count
        response_data = []
        if page <= total_page:
            paginated_entities = paginator.get_page(page)
            for entity_upload in paginated_entities:
                entity = (
                    entity_upload.revised_geographical_entity if
                    entity_upload.revised_geographical_entity else
                    entity_upload.original_geographical_entity
                )
                is_importable_func = module_function(
                    dataset.module.code_name,
                    'qc_validation',
                    'is_validation_result_importable')
                is_importable, is_warning = is_importable_func(
                    entity_upload,
                    request.user
                )
                tz = timezone(settings.TIME_ZONE)
                error_logs = None
                if entity_upload.status == PROCESSING_ERROR:
                    error_logs = (
                        entity_upload.logs if entity_upload.logs else None
                    )
                response_data.append({
                    'id': entity_upload.id,
                    'country': (
                        entity.label
                        if entity
                        else entity_upload.revised_entity_name
                    ),
                    'started at': entity_upload.started_at.astimezone(tz)
                    .strftime(f"%d %B %Y %H:%M:%S {settings.TIME_ZONE}"),
                    'status': self.get_status(entity_upload.status),
                    'error_summaries': self.sort_error_summaries(
                        entity_upload.summaries),
                    'error_report': (
                        entity_upload.error_report.url if
                        entity_upload.error_report else ''
                    ),
                    'is_importable': is_importable,
                    'is_warning': is_warning,
                    'progress': entity_upload.progress,
                    'error_logs': error_logs
                })
        return Response(
            status=200,
            data={
                'count': total_count,
                'page': page,
                'total_page': total_page,
                'page_size': page_size,
                'is_read_only': upload_session.is_read_only(),
                'is_all_finished': is_all_finished,
                'results': response_data,
                'summary': job_summaries
            }
        )


class Level1UploadSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    default_code = serializers.SerializerMethodField()
    old_parent = serializers.SerializerMethodField()
    new_parent = serializers.SerializerMethodField()
    is_rematched = serializers.SerializerMethodField()
    overlap = serializers.SerializerMethodField()

    def get_label(self, obj: EntityUploadChildLv1):
        return obj.entity_name

    def get_default_code(self, obj: EntityUploadChildLv1):
        return obj.entity_id

    def get_old_parent(self, obj: EntityUploadChildLv1):
        return obj.parent_entity_id

    def get_new_parent(self, obj: EntityUploadChildLv1):
        if 'upload' in self.context:
            entity_upload = self.context['upload']
            if entity_upload.original_geographical_entity:
                return (
                    entity_upload.original_geographical_entity.internal_code
                )
            return entity_upload.revised_entity_id
        return '-'

    def get_is_rematched(self, obj: EntityUploadChildLv1):
        return 'Yes' if obj.is_parent_rematched else 'No'

    def get_overlap(self, obj: EntityUploadChildLv1):
        d = (
            round(obj.overlap_percentage, 2)
            if obj.overlap_percentage
            else 0
        )
        return d

    class Meta:
        model = EntityUploadChildLv1
        fields = [
            'id',
            'label',
            'default_code',
            'old_parent',
            'new_parent',
            'is_rematched',
            'overlap'
        ]


class EntityUploadLevel1List(AzureAuthRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        entity_upload_id = request.GET.get('id', None)
        entity_upload = EntityUploadStatus.objects.get(
            id=entity_upload_id
        )
        level1 = EntityUploadChildLv1.objects.filter(
            entity_upload=entity_upload
        ).order_by('overlap_percentage')
        return Response(
            status=200,
            data=Level1UploadSerializer(
                level1,
                many=True,
                context={
                    'upload': entity_upload
                }
            ).data
        )


class OverlapsEntitySerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    id_1 = serializers.SerializerMethodField()
    label_1 = serializers.SerializerMethodField()
    default_code_1 = serializers.SerializerMethodField()
    id_2 = serializers.SerializerMethodField()
    label_2 = serializers.SerializerMethodField()
    default_code_2 = serializers.SerializerMethodField()
    overlaps_percentage = serializers.SerializerMethodField()
    overlaps_area = serializers.SerializerMethodField()

    def get_level(self, obj):
        return obj.get('level', '')

    def get_id_1(self, obj):
        return obj.get('geo1_id', '')

    def get_label_1(self, obj):
        return obj.get('geo1_label', '')

    def get_default_code_1(self, obj):
        return obj.get('geo1_code', '')

    def get_id_2(self, obj):
        return obj.get('geo2_id', '')

    def get_label_2(self, obj):
        return obj.get('geo2_label', '')

    def get_default_code_2(self, obj):
        return obj.get('geo2_code', '')

    def get_overlaps_percentage(self, obj):
        overlaps = obj.get('percentage', 0)
        return f'{overlaps:.2f}'

    def get_overlaps_area(self, obj):
        overlaps = obj.get('overlaps_area', 0)
        if overlaps < 1e-4:
            return f'{overlaps:.8f} km²'
        return f'{overlaps:.4f} km²'

    class Meta:
        model = GeographicalEntity
        fields = [
            'level',
            'id_1',
            'label_1',
            'default_code_1',
            'id_2',
            'label_2',
            'default_code_2',
            'overlaps_percentage',
            'overlaps_area'
        ]


class OverlapsEntityUploadList(AzureAuthRequiredMixin, APIView):
    """
    Fetch overlaps entities in same level from EntityUpload
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        upload_id = kwargs.get('upload_id')
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=upload_id
        )
        ancestor = entity_upload.revised_geographical_entity
        level = request.GET.get('level', None)
        dataset = entity_upload.upload_session.dataset
        raw_sql = (
            'select gg_1.level as level, '
            'gg_1.id as geo1_id, gg_1.label as geo1_label, '
            'gg_1.internal_code as geo1_code, '
            'gg_2.id as geo2_id, gg_2.label as geo2_label, '
            'gg_2.internal_code as geo2_code, '
            'ST_AREA(ST_INTERSECTION(gg_1.geometry, gg_2.geometry), '
            ' true)/10^6 '
            'as overlaps_area, '
            '100*ST_AREA(ST_INTERSECTION(gg_1.geometry, gg_2.geometry),'
            ' true)/ST_AREA(gg_2.geometry, true) '
            'as percentage '
            'from georepo_geographicalentity gg_1 '
            'INNER JOIN georepo_geographicalentity gg_2 ON '
            '    gg_2.dataset_id=gg_1.dataset_id '
            '    AND gg_1.id <> gg_2.id and gg_1.level=gg_2.level '
            '    and gg_1.layer_file_id = gg_2.layer_file_id '
            '    AND ST_OVERLAPS(gg_1.geometry, gg_2.geometry) '
            'where gg_1.dataset_id=%s '
            'AND (gg_1.id=%s OR gg_1.ancestor_id=%s) '
        )
        query_values = [dataset.id,
                        ancestor.id, ancestor.id]
        if level is not None:
            raw_sql = (
                raw_sql + ' AND gg_1.level=%s'
            )
            query_values.append(level)
        results = {}
        with connection.cursor() as cursor:
            cursor.execute(raw_sql, query_values)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            for row in rows:
                data = dict(zip(columns, row))
                key = f'{min(row[1], row[4])}_{max(row[1], row[4])}'
                if key not in results:
                    results[key] = data
        return Response(
            status=200,
            data=OverlapsEntitySerializer(results.values(), many=True).data
        )


class OverlapsEntityUploadDetail(AzureAuthRequiredMixin, APIView):
    """
    Get the detail of overlaps area to be highlighted in map
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        entity_id_1 = kwargs.get('entity_id_1')
        entity_id_2 = kwargs.get('entity_id_2')
        entity_1 = get_object_or_404(
            GeographicalEntity,
            id=entity_id_1
        )
        entity_2 = get_object_or_404(
            GeographicalEntity,
            id=entity_id_2
        )
        union = (
            entity_1.geometry.union(entity_2.geometry)
        )
        bbox = union.extent
        overlaps = entity_1.geometry.intersection(
            entity_2.geometry
        )
        return Response(
            status=200,
            data={
                'geometry_1': (
                    json.loads(
                        entity_1.geometry.geojson
                    )
                ),
                'geometry_2': (
                    json.loads(
                        entity_2.geometry.geojson
                    )
                ),
                'bbox': bbox,
                'overlaps': (
                    json.loads(
                        overlaps.geojson
                    )
                )
            }
        )


class RetriggerSingleValidation(AzureAuthRequiredMixin, APIView):
    """
    Retrigger validation of single entity upload status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        upload_id = kwargs.get('upload_id')
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=upload_id
        )
        entity_upload.started_at = django_tz.now()
        entity_upload.status = STARTED
        entity_upload.logs = ''
        entity_upload.summaries = None
        entity_upload.error_report = None
        if entity_upload.task_id:
            cancel_task(entity_upload.task_id)
        entity_upload.save(update_fields=['started_at', 'status', 'logs',
                                          'summaries', 'error_report'])
        upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
            entity_upload_status=entity_upload
        )
        # trigger validation task
        task = validate_ready_uploads.apply_async(
            (
                entity_upload.id,
                upload_log.id
            ),
            queue='validation'
        )
        entity_upload.task_id = task.id
        entity_upload.save(update_fields=['task_id'])
        return Response(
            status=200,
            data={
                'detail': 'Success'
            }
        )
