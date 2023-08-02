import re
import uuid
import os.path
import math
from django.db.models.expressions import RawSQL, Q
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import connection
from django.http import Http404, HttpResponseForbidden, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from azure_auth.backends import AzureAuthRequiredMixin
from celery.result import AsyncResult
from core.celery import app
from dashboard.serializers.view import (
    DatasetViewSerializer, DatasetViewDetailSerializer
)
from georepo.models import (
    Dataset,
    DatasetView,
    TagWithDescription,
    GeographicalEntity
)
from dashboard.models.entities_user_config import EntitiesUserConfig
from georepo.restricted_sql_commands import RESTRICTED_COMMANDS
from georepo.models.dataset_view import (
    DATASET_VIEW_ALL_VERSIONS_TAG,
    DATASET_VIEW_LATEST_TAG,
    DATASET_VIEW_DATASET_TAG,
    DATASET_VIEW_SUBSET_TAG,
    DatasetViewResource
)
from georepo.utils.dataset_view import (
    trigger_generate_vector_tile_for_view,
    create_sql_view,
    init_view_privacy_level
)
from georepo.tasks.simplify_geometry import simplify_geometry_in_view
from georepo.utils.permission import (
    check_user_has_view_permission,
    get_views_for_user,
    get_view_permission_privacy_level
)
from georepo.utils.exporter_base import APIDownloaderBase


TABLE_NAMES = [
    'geographicalentity',
    'entityname',
    'entitycode'
]

RESTRICTED_TAGS = [
    DATASET_VIEW_LATEST_TAG,
    DATASET_VIEW_ALL_VERSIONS_TAG,
    DATASET_VIEW_DATASET_TAG,
    DATASET_VIEW_SUBSET_TAG
]


class QueryStringCheck(object):
    """
    Check query string, and update the tables
    """
    query_string = ""
    extra_fields = {}

    def check_query(self):
        for prohibited_command in RESTRICTED_COMMANDS:
            if prohibited_command in self.query_string.lower():
                return False

        if ';' not in self.query_string:
            self.query_string += ';'

        # Update table name, add georepo prefix
        for table_name in TABLE_NAMES:
            georepo_table_name = f'georepo_{table_name}'
            if (
                table_name in self.query_string and
                georepo_table_name not in self.query_string
            ):
                self.query_string = self.query_string.replace(
                    table_name,
                    georepo_table_name
                )

        if self.extra_fields:
            is_first_cond = False
            if 'where' not in self.query_string.lower():
                self.query_string = (
                    self.query_string.replace(
                        ';', ' WHERE ;')
                )
                is_first_cond = True
            for (key, value) in self.extra_fields.items():
                if key not in self.query_string:
                    if 'join' in self.query_string.lower():
                        # This is join table, get the first table name
                        join_tag = 'join'
                        if 'left' in self.query_string.lower():
                            join_tag = 'left'
                        if 'right' in self.query_string.lower():
                            join_tag = 'right'
                        key = re.search(
                            r'(\w+\s*)' + join_tag, self.query_string.lower()
                        ).group(1).strip() + '.' + key
                    and_cond = 'AND'
                    if is_first_cond:
                        and_cond = ''
                        is_first_cond = False
                    self.query_string = (
                        self.query_string.replace(
                            ';', f' {and_cond} {key}={value};')
                    )
        return True


class DatasetViewReadPermission(UserPassesTestMixin):
    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_view = get_object_or_404(
            DatasetView,
            id=self.kwargs.get('id')
        )
        privacy_level = get_view_permission_privacy_level(
            self.request.user, dataset_view.dataset,
            dataset_view=dataset_view)
        return (
            check_user_has_view_permission(
                self.request.user,
                dataset_view,
                privacy_level) and
            privacy_level >= dataset_view.min_privacy_level
        )


class DatasetViewManagePermission(UserPassesTestMixin):
    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_view = get_object_or_404(
            DatasetView,
            id=self.kwargs.get('id')
        )
        return self.request.user.has_perm('edit_metadata_dataset_view',
                                          dataset_view)


class DatasetViewOwnPermission(UserPassesTestMixin):
    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def test_func(self):
        dataset_view = get_object_or_404(
            DatasetView,
            id=self.kwargs.get('id')
        )
        return (
            self.request.user.has_perm(
                'edit_query_dataset_view',
                dataset_view
            ) and
            self.request.user.has_perm('delete_datasetview',
                                       dataset_view)
        )


class ViewDetail(AzureAuthRequiredMixin,
                 DatasetViewReadPermission, APIView):
    """
    API to get detail of the view
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        dataset_view = DatasetView.objects.get(
            id=self.kwargs.get('id'))
        return Response(
            DatasetViewDetailSerializer(
                dataset_view,
                many=False,
                context={
                    'user': self.request.user
                }
            ).data
        )


class ViewList(AzureAuthRequiredMixin, APIView):
    """
    API view to list views
    """
    permission_classes = [IsAuthenticated]

    def _filter_tags(self, request):
        tags = dict(request.data).get('tags', [])
        if not tags:
            return {}
        return {'tags__name__in': tags}

    def _filter_mode(self, request):
        mode = dict(request.data).get('mode', [])
        if not mode or sorted(mode) == ['Dynamic', 'Static']:
            return {}

        return {'is_static': True if mode[0] == 'Static' else False}

    def _filter_dataset(self, request):
        dataset = dict(request.data).get('dataset', [])
        if not dataset:
            return {}

        return {'dataset__label__in': dataset}

    def _filter_is_default(self, request):
        is_default = dict(request.data).get('is_default', [])
        if not is_default or sorted(is_default) == ['No', 'Yes']:
            return {}

        return {'default_type': True if is_default[0] == 'Yes' else False}

    def _filter_min_privacy(self, request):
        min_privacy = dict(request.data).get('min_privacy', [])
        if not min_privacy:
            return {}

        return {'min_privacy_level__in': min_privacy}

    def _filter_max_privacy(self, request):
        max_privacy = dict(request.data).get('max_privacy', [])
        if not max_privacy:
            return {}

        return {'max_privacy_level__in': max_privacy}

    def _filter_queryset(self, queryset, request):
        filter_kwargs = {}
        filter_kwargs.update(self._filter_tags(request))
        filter_kwargs.update(self._filter_mode(request))
        filter_kwargs.update(self._filter_dataset(request))
        filter_kwargs.update(self._filter_min_privacy(request))
        filter_kwargs.update(self._filter_max_privacy(request))
        return queryset.filter(**filter_kwargs)

    def _search_queryset(self, queryset, request):
        search_text = request.data.get('search_text', '')
        if not search_text:
            return queryset
        char_fields = [
            field.name for field in DatasetView.get_fields() if
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
        sort_by = request.query_params.get('sort_by', 'name')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        if not sort_by:
            sort_by = 'name'
        if not sort_direction:
            sort_direction = 'asc'
        ordering = sort_by if sort_direction == 'asc' else f"-{sort_by}"
        queryset = queryset.order_by(ordering)
        return queryset

    def post(self, *args, **kwargs):
        (
            user_privacy_levels,
            views_querysets
        ) = get_views_for_user(self.request.user)
        # It seems we cannot use values_list on views_queryset
        views_querysets = DatasetView.objects.\
            filter(id__in=[v.id for v in views_querysets])
        views_querysets = self._search_queryset(views_querysets, self.request)
        views_querysets = self._filter_queryset(views_querysets, self.request)
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.query_params.get('page_size', '10'))
        views_querysets = self._sort_queryset(views_querysets, self.request)
        paginator = Paginator(views_querysets, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = DatasetViewSerializer(
                paginated_entities,
                many=True,
                context={
                    'user': self.request.user,
                    'user_privacy_levels': user_privacy_levels
                }
            ).data

        return Response({
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output,
        })


class ViewFilterValue(
    AzureAuthRequiredMixin,
    APIView
):
    """
    Get filter value for given View and criteria
    """
    permission_classes = [IsAuthenticated]
    views_querysets = DatasetView.objects.none()

    def get_user_views(self):
        _, views_querysets = get_views_for_user(self.request.user)
        views_querysets = DatasetView.objects.filter(
            id__in=[v.id for v in views_querysets]
        )
        return views_querysets

    def fetch_tags(self):
        tags = self.views_querysets.order_by().\
            values_list('tags__name', flat=True).distinct()
        return [tag for tag in tags if tag]

    def fetch_mode(self):
        return [
            'Static',
            'Dynamic'
        ]

    def fetch_dataset(self):
        return list(self.views_querysets.exclude(
            dataset__label__isnull=True
        ).exclude(
            dataset__label__exact=''
        ).order_by().values_list('dataset__label', flat=True).distinct())

    def fetch_is_default(self):
        return [
            'No',
            'Yes'
        ]

    def fetch_min_privacy(self):
        return list(self.views_querysets.order_by().\
            values_list('min_privacy_level', flat=True).distinct())

    def fetch_max_privacy(self):
        return list(self.views_querysets.order_by().\
            values_list('max_privacy_level', flat=True).distinct())

    def get(self, request, criteria, *args, **kwargs):
        self.views_querysets = self.get_user_views()
        try:
            data = eval(f"self.fetch_{criteria}()")
        except AttributeError:
            data = []
        return Response(status=200, data=data)


class SQLColumnsTablesList(APIView):
    """
    Api view to list all columns and tables for sql query
    """
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        columns = []
        cursor = connection.cursor()
        for table in TABLE_NAMES:
            query = (
                'SELECT * ' +
                'FROM INFORMATION_SCHEMA.COLUMNS '
                f'WHERE TABLE_NAME = \'georepo_{table}\''
            )
            try:
                cursor.execute('''%s''' % query)
                data = cursor.fetchall()
                for column in data:
                    columns.append(
                        f'{table}.{column[3]}'
                    )
                    if table == TABLE_NAMES[0]:
                        columns.append(
                            column[3]
                        )
            except Exception:  # noqa
                pass
            cursor.close()
        return Response({
            'tables': TABLE_NAMES,
            'columns': columns
        })


class DeleteView(AzureAuthRequiredMixin,
                 DatasetViewOwnPermission, APIView):
    """
    API view to delete a view
    """
    def post(self, *args, **kwargs):
        dataset_view = DatasetView.objects.get(
            id=self.kwargs.get('id'))
        if dataset_view.default_type is not None:
            raise ValidationError(
                'Unable to remove default view!'
            )
        dataset_view.delete()
        return Response(status=200)


class UpdateView(AzureAuthRequiredMixin,
                 DatasetViewOwnPermission, APIView, QueryStringCheck):
    """
    API view to update a view
    """
    def post(self, request, **kwargs):
        dataset_view = get_object_or_404(
            DatasetView,
            id=self.kwargs.get('id')
        )
        # check for deprecated dataset
        if not dataset_view.dataset.is_active:
            return Response(data={
                'detail': 'Unable to update view in deprecated dataset',
            }, status=400)
        self.query_string = request.data.get('query_string', '')
        dataset_view.name = request.data.get('name', '')
        dataset_view.description = request.data.get('description', '')
        tags = request.data.get('tags', [])
        dataset_view.tags.clear()

        if len(tags) > 0:
            for tag_name in tags:
                if tag_name.strip():
                    dataset_view.tags.add(tag_name.strip())

        dataset_view.dataset = Dataset.objects.get(
            id=request.data.get('dataset_id')
        )
        dataset_view.mode = request.data.get('mode', '')
        self.extra_fields = {
            'dataset_id': dataset_view.dataset.id
        }
        query_valid = self.check_query()
        if not query_valid:
            raise Http404('Query invalid')

        should_generate_vector_tiles = False
        if self.query_string != dataset_view.query_string:
            dataset_view.query_string = self.query_string
            should_generate_vector_tiles = True

        dataset_view.save()
        if should_generate_vector_tiles:
            create_sql_view(dataset_view)
            init_view_privacy_level(dataset_view)
            if not settings.DEBUG:
                # Trigger simplification
                if dataset_view.simplification_task_id:
                    res = AsyncResult(dataset_view.simplification_task_id)
                    if not res.ready():
                        app.control.revoke(
                            dataset_view.simplification_task_id,
                            terminate=True
                        )
                task_simplify = (
                    simplify_geometry_in_view.delay(dataset_view.id)
                )
                dataset_view.simplification_task_id = task_simplify.id
                dataset_view.simplification_progress = 'Started'
                dataset_view.save(
                    update_fields=['simplification_task_id',
                                   'simplification_progress']
                )
                trigger_generate_vector_tile_for_view(dataset_view)
        return Response(status=200)


class CreateNewView(AzureAuthRequiredMixin,
                    APIView, QueryStringCheck):
    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        name = request.data.get('name', '')
        description = request.data.get('description', '')
        dataset = Dataset.objects.get(
            id=request.data.get('dataset_id')
        )
        # check for deprecated dataset
        if not dataset.is_active:
            return Response(data={
                'detail': 'Unable to create new view in deprecated dataset',
            }, status=400)
        mode = request.data.get('mode', '')
        self.query_string = request.data.get('query_string', '')
        self.extra_fields = {
            'dataset_id': dataset.id
        }
        query_valid = self.check_query()
        tags = request.data.get('tags', [])

        if not query_valid:
            raise Http404('Query invalid')

        if not name or not description or not mode or not self.query_string:
            raise Http404('Missing required field')

        dataset_view = DatasetView.objects.create(
            name=name,
            description=description,
            dataset=dataset,
            is_static=mode == 'static',
            query_string=self.query_string,
            created_by=self.request.user
        )

        if len(tags) > 0:
            for tag_name in tags:
                if tag_name.strip():
                    dataset_view.tags.add(tag_name.strip())

        dataset_view.save()
        create_sql_view(dataset_view)
        init_view_privacy_level(dataset_view)
        trigger_generate_vector_tile_for_view(dataset_view)

        return Response(status=201)


class GetViewTags(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        data = TagWithDescription.objects.exclude(
            name__in=RESTRICTED_TAGS
        ).values_list('name', flat=True)
        return Response(
            status=200,
            data=data
        )


class QueryViewCheck(APIView, QueryStringCheck):
    """Check whether the query string is valid or not"""
    permission_classes = [IsAuthenticated]

    def post(self, *args, **kwargs):
        self.query_string = self.request.data.get('query_string')
        dataset = self.request.data.get('dataset', None)
        dataset = Dataset.objects.get(
            id=dataset
        )
        self.extra_fields = {
            'dataset_id': dataset.id
        }
        query_valid = self.check_query()
        if not query_valid:
            return Response(data={
                'valid': False,
                'total': 0
            })

        cursor = connection.cursor()
        total_count = 0
        try:
            clean_query = self.query_string.replace(';', '')
            sql = f'SELECT COUNT(*) FROM ({clean_query}) AS custom_view'
            cursor.execute(sql)
            total_count = cursor.fetchone()[0]
            cursor.close()
            connection.commit()
        except Exception as ex: # noqa
            print(ex)
            connection.rollback()
            return Response(data={
                'valid': False,
                'total': 0
            })
        return Response(data={
            'valid': True,
            'total': total_count
        })


class QueryViewPreview(APIView, QueryStringCheck):
    """Create EntitiesUserConfig with raw query"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        self.query_string = self.request.data.get('query_string')
        dataset = self.request.data.get('dataset', None)
        session = self.request.data.get('session', str(uuid.uuid4()))
        dataset = Dataset.objects.get(
            id=dataset
        )
        self.extra_fields = {
            'dataset_id': dataset.id
        }
        query_valid = self.check_query()
        if not query_valid:
            raise Http404('Query invalid')

        config, _ = EntitiesUserConfig.objects.update_or_create(
            dataset=dataset,
            user=request.user,
            uuid=session,
            defaults={
                'query_string': self.query_string
            }
        )

        return Response(data={
            'session': config.uuid
        })


class DownloadView(AzureAuthRequiredMixin,
                   DatasetViewReadPermission,
                   APIDownloaderBase):
    """
    API to download view based on session user config
    """
    permission_classes = [IsAuthenticated]

    def download_view(self, dataset_view, filter_levels=[]):
        output_format = self.get_output_format()
        # retrieve user privacy level for this dataset
        user_privacy_level = get_view_permission_privacy_level(
            self.request.user,
            dataset_view.dataset,
            dataset_view=dataset_view
        )
        # get resource for the privacy level
        resource = DatasetViewResource.objects.filter(
            dataset_view=dataset_view,
            privacy_level=user_privacy_level
        ).first()
        if resource is None:
            raise Http404('The requested file does not exist')
        result_list = []
        total_count = 0
        entities = GeographicalEntity.objects.filter(
            dataset=dataset_view.dataset,
            is_approved=True,
            privacy_level__lte=user_privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        levels = entities.order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        total_count = 0
        for level in levels:
            if filter_levels and level not in filter_levels:
                continue
            exported_name = f'adm{level}'
            file_path = os.path.join(
                output_format['directory'],
                str(resource.uuid),
                exported_name
            ) + output_format['suffix']
            if not os.path.exists(file_path):
                raise Http404('The requested file does not exist')
            result_list.append(file_path)
            # add metadata (for geojson)
            metadata_file_path = os.path.join(
                output_format['directory'],
                str(resource.uuid),
                exported_name
            ) + '.xml'
            if os.path.exists(metadata_file_path):
                result_list.append(metadata_file_path)
            total_count += 1
        self.append_readme(resource, output_format, result_list)
        if total_count == 0:
            raise Http404('The requested file does not exist')
        prefix_name, zip_file_name = self.get_output_names(dataset_view)
        return self.prepare_response(prefix_name, zip_file_name, result_list)

    def download_filtered_view(self, dataset_view: DatasetView,
                               config: EntitiesUserConfig):
        country = (
            config.filters['country'][0] if
            len(config.filters['country']) else ''
        )
        levels = []
        if config.filters['level']:
            levels = [int(level) for level in config.filters['level']]
        if (
            dataset_view.default_ancestor_code is None and
            not dataset_view.is_static and dataset_view.default_type
        ):
            # filter by country if it's default view with many countries
            if country:
                # find correct view based on the country
                ancestor = GeographicalEntity.objects.filter(
                    dataset=dataset_view.dataset,
                    level=0,
                    label=country,
                    is_approved=True
                ).first()
                if not ancestor:
                    raise Http404('The requested file does not exist')
                country_view = DatasetView.objects.filter(
                    dataset=dataset_view.dataset,
                    default_type=dataset_view.default_type,
                    is_static=False,
                    default_ancestor_code=ancestor.unique_code
                ).first()
                if not country_view:
                    raise Http404('The requested file does not exist')
                return self.download_view(country_view, levels)
            else:
                return self.download_view(dataset_view, levels)
        else:
            # contains single country
            return self.download_view(dataset_view, levels)

    def check_session_has_filter(self, session_uuid):
        user_config = EntitiesUserConfig.objects.filter(
            uuid=session_uuid
        ).first()
        if not user_config or not user_config.filters:
            return None
        if (
            'country' not in user_config.filters and
            'level' not in user_config.filters
        ):
            return None
        if (
            len(user_config.filters['country']) == 0 and
            len(user_config.filters['level']) == 0
        ):
            return None
        return user_config

    def get(self, *args, **kwargs):
        view_id = kwargs.get('id', None)
        dataset_view = get_object_or_404(
            DatasetView,
            id=view_id,
            dataset__module__is_active=True
        )
        session = self.request.GET.get('session', None)
        sessionObj = self.check_session_has_filter(session)
        response: HttpResponse
        if sessionObj is None:
            # download whole view
            response = self.download_view(dataset_view)
        else:
            # download view with filter
            response = self.download_filtered_view(dataset_view, sessionObj)
        return response
