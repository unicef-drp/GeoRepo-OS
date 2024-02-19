import re
import uuid
import math
import logging
from django.db.models.expressions import Q
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import connection
from django.http import Http404, HttpResponseForbidden
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.serializers.view import (
    DatasetViewSerializer, DatasetViewDetailSerializer
)
from georepo.models import (
    Dataset,
    DatasetView,
    TagWithDescription
)
from dashboard.models.entities_user_config import EntitiesUserConfig
from georepo.restricted_sql_commands import RESTRICTED_COMMANDS
from georepo.models.dataset_view import (
    DATASET_VIEW_ALL_VERSIONS_TAG,
    DATASET_VIEW_LATEST_TAG,
    DATASET_VIEW_DATASET_TAG,
    DATASET_VIEW_SUBSET_TAG
)
from georepo.utils.dataset_view import (
    create_sql_view,
    init_view_privacy_level,
    calculate_entity_count_in_view
)
from georepo.utils.permission import (
    check_user_has_view_permission,
    get_views_for_user,
    get_view_permission_privacy_level
)


logger = logging.getLogger(__name__)

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
            search_reqex = r'\b' + re.escape(prohibited_command) + r'\b'
            if re.search(search_reqex, self.query_string, re.IGNORECASE):
                logger.error(
                    'Invalid query: '
                    f'prohibited command {prohibited_command}!'
                )
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
        # replace double qoutes with single quote
        self.query_string = (
            self.query_string.replace('"', '\'')
        )
        return True


class DatasetViewBasePermission(UserPassesTestMixin):

    def handle_no_permission(self):
        return HttpResponseForbidden('No permission')

    def get_dataset_view(self):
        id = self.kwargs.get('id')
        if id.isnumeric():
            dataset_view = get_object_or_404(
                DatasetView,
                id=id
            )
        else:
            dataset_view = get_object_or_404(
                DatasetView,
                uuid=id
            )
        return dataset_view


class DatasetViewReadPermission(DatasetViewBasePermission):

    def test_func(self):
        dataset_view = self.get_dataset_view()
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


class DatasetViewManagePermission(DatasetViewBasePermission):

    def test_func(self):
        dataset_view = self.get_dataset_view()
        return self.request.user.has_perm('edit_metadata_dataset_view',
                                          dataset_view)


class DatasetViewOwnPermission(DatasetViewBasePermission):

    def test_func(self):
        dataset_view = self.get_dataset_view()
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
        dataset_view = self.get_dataset_view()
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
        return queryset.filter(**filter_kwargs).distinct()

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

        ordering_mapping = {
            'dataset': 'dataset__label'
        }
        sort_by = ordering_mapping.get(sort_by, sort_by)
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
        return list(
            Dataset.objects.all().order_by(
                'label').values_list('label', flat=True).distinct())

    def fetch_is_default(self):
        return [
            'No',
            'Yes'
        ]

    def fetch_min_privacy(self):
        return list(
            self.views_querysets.order_by().
            values_list('min_privacy_level', flat=True).distinct()
        )

    def fetch_max_privacy(self):
        return list(
            self.views_querysets.order_by().
            values_list('max_privacy_level', flat=True).distinct()
        )

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

        if self.query_string != dataset_view.query_string:
            dataset_view.query_string = self.query_string
            dataset_view = dataset_view.set_out_of_sync(
                tiling_config=False,
                vector_tile=True,
                centroid=True,
                save=False
            )
        dataset_view.save()
        create_sql_view(dataset_view)
        init_view_privacy_level(dataset_view)
        calculate_entity_count_in_view(dataset_view)
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
        dataset_view = dataset_view.set_out_of_sync(
            tiling_config=False,
            vector_tile=True,
            centroid=True,
            save=False
        )

        if len(tags) > 0:
            for tag_name in tags:
                if tag_name.strip():
                    dataset_view.tags.add(tag_name.strip())

        dataset_view.save()
        create_sql_view(dataset_view)
        init_view_privacy_level(dataset_view)
        calculate_entity_count_in_view(dataset_view)
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
