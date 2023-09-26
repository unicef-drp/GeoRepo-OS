import re
import time
from math import isclose
from typing import List
from django.db import connection
from django.db.models import Avg
from celery.result import AsyncResult
from core.celery import app
from django.db.models.expressions import RawSQL
from django.db.models import Max, Min
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import (
    DatasetView,
    DATASET_VIEW_LATEST_TAG,
    DATASET_VIEW_ALL_VERSIONS_TAG,
    DATASET_VIEW_DATASET_TAG,
    DATASET_VIEW_SUBSET_TAG,
    DatasetViewResource
)
from georepo.models.entity import GeographicalEntity
from georepo.restricted_sql_commands import RESTRICTED_COMMANDS

VIEW_LATEST_DESC = (
    'This dataset contains only the latest entities from main dataset'
)
VIEW_ALL_VERSIONS_DESC = (
    'This dataset contains all the entities from main dataset'
)


def trigger_generate_dynamic_views(dataset: Dataset,
                                   adm0: GeographicalEntity = None,
                                   export_data: bool = True,
                                   adm0_list=[]):
    """
    Trigger generate vector tiles for dynamic views for this dataset
    If adm0 is provided, then this refresh is because adm0 entity is updated
    """
    dynamic_dataset_views = DatasetView.objects.filter(
        dataset=dataset,
        is_static=False
    )
    for dataset_view in dynamic_dataset_views:
        if (
            dataset_view.default_type and adm0 is not None and
            dataset_view.default_ancestor_code is not None
        ):
            # this is default view for specific country
            # skip refresh if it's not updated
            if adm0.unique_code != dataset_view.default_ancestor_code:
                continue
        if (
            dataset_view.default_type and len(adm0_list) > 0 and
            dataset_view.default_ancestor_code is not None
        ):
            # skip refresh if default_ancestor_code is not in adm0_list
            if dataset_view.default_ancestor_code not in adm0_list:
                continue
        # update max and min privacy level of entities in view
        init_view_privacy_level(dataset_view)
        generate_view_bbox(dataset_view)


def trigger_generate_vector_tile_for_view(dataset_view: DatasetView,
                                          export_data: bool = True):
    """
    Trigger generate vector tiles for a view
    """
    from dashboard.tasks import (
        view_vector_tiles_task
    )
    dataset_view.vector_tile_sync_status = DatasetView.SyncStatus.SYNCING
    dataset_view.vector_tiles_progress = 0
    if export_data:
        dataset_view.product_sync_status = DatasetView.SyncStatus.SYNCING
        dataset_view.product_progress = 0
    if dataset_view.task_id:
        res = AsyncResult(dataset_view.task_id)
        if not res.ready():
            # find if there is running task and stop it
            app.control.revoke(
                dataset_view.task_id,
                terminate=True,
                signal='SIGKILL'
            )
    dataset_view.save()
    task = view_vector_tiles_task.delay(dataset_view.id, export_data)
    dataset_view.task_id = task.id
    dataset_view.save(update_fields=['task_id'])


def generate_default_view_dataset_latest(
        dataset: Dataset) -> List[DatasetView]:
    # check for existing
    default_view = DatasetView.objects.filter(
        dataset=dataset,
        default_type=DatasetView.DefaultViewType.IS_LATEST,
        default_ancestor_code__isnull=True
    )
    if default_view.exists():
        return []
    sql = (
        'select * from georepo_geographicalentity '
        f'where dataset_id={dataset.id} '
        'and is_latest=true and is_approved=true;'
    )
    view_name = f'{dataset.label} (Latest)'
    view_desc = VIEW_LATEST_DESC
    if dataset.description:
        view_desc = (
            dataset.description + '. ' +
            view_desc
        )
    dataset_view = DatasetView.objects.create(
        name=view_name,
        description=view_desc,
        dataset=dataset,
        is_static=False,
        query_string=sql,
        default_type=DatasetView.DefaultViewType.IS_LATEST,
        created_by=dataset.created_by
    )
    dataset_view.tags.add(DATASET_VIEW_LATEST_TAG)
    dataset_view.tags.add(DATASET_VIEW_DATASET_TAG)
    create_sql_view(dataset_view)
    return [dataset_view]


def generate_default_view_dataset_all_versions(
        dataset: Dataset) -> List[DatasetView]:
    # check for existing
    default_view = DatasetView.objects.filter(
        dataset=dataset,
        default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
        default_ancestor_code__isnull=True
    )
    if default_view.exists():
        return []
    sql = (
        'select * from georepo_geographicalentity '
        f'where dataset_id={dataset.id} and is_approved=true;'
    )
    view_name = f'{dataset.label} (All Versions)'
    view_desc = VIEW_ALL_VERSIONS_DESC
    if dataset.description:
        view_desc = (
            dataset.description + '. ' +
            view_desc
        )
    dataset_view = DatasetView.objects.create(
        name=view_name,
        description=view_desc,
        dataset=dataset,
        is_static=False,
        query_string=sql,
        default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
        created_by=dataset.created_by
    )
    dataset_view.tags.add(DATASET_VIEW_ALL_VERSIONS_TAG)
    dataset_view.tags.add(DATASET_VIEW_DATASET_TAG)
    create_sql_view(dataset_view)
    return [dataset_view]


def generate_default_view_adm0_latest(dataset: Dataset) -> List[DatasetView]:
    # check for existing
    existing_ancestors = DatasetView.objects.filter(
        dataset=dataset,
        default_type=DatasetView.DefaultViewType.IS_LATEST
    ).exclude(
        default_ancestor_code__isnull=True
    ).values_list('default_ancestor_code', flat=True)
    # find all adm0 in current dataset
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_latest=True,
        is_approved=True
    )
    adm0_entities = entities.values_list('unique_code', flat=True)
    # check for deleted adm0
    for existing in existing_ancestors:
        if existing not in adm0_entities:
            view = DatasetView.objects.filter(
                dataset=dataset,
                default_type=DatasetView.DefaultViewType.IS_LATEST,
                default_ancestor_code=existing
            ).first()
            if view:
                view.delete()
    # check for new adm0
    views = []
    for adm0 in adm0_entities:
        if adm0 not in existing_ancestors:
            entity = entities.filter(
                unique_code=adm0
            ).first()
            adm0_name = entity.label if entity else adm0
            # create new DatasetView
            view_name = f'{dataset.label} - {adm0_name} (Latest)'
            view_desc = f'{VIEW_LATEST_DESC} for {adm0_name}'
            if dataset.description:
                view_desc = (
                    dataset.description + '. ' +
                    view_desc
                )
            sql = (
                'select gg.* from georepo_geographicalentity gg '
                'left join georepo_geographicalentity ancestor on '
                'ancestor.id=gg.ancestor_id '
                f'where gg.dataset_id={dataset.id} '
                'and gg.is_latest=true and gg.is_approved=true '
            )
            sql = (
                sql +
                'AND (('
                'ancestor.id IS NULL '
                f"AND gg.unique_code='{adm0}') "
                'OR ('
                f"ancestor.unique_code='{adm0}'"
                '));'
            )
            dataset_view = DatasetView.objects.create(
                name=view_name,
                description=view_desc,
                dataset=dataset,
                is_static=False,
                query_string=sql,
                default_type=DatasetView.DefaultViewType.IS_LATEST,
                default_ancestor_code=adm0,
                created_by=dataset.created_by
            )
            dataset_view.tags.add(DATASET_VIEW_LATEST_TAG)
            dataset_view.tags.add(DATASET_VIEW_SUBSET_TAG)
            views.append(dataset_view)
            create_sql_view(dataset_view)
    return views


def generate_default_view_adm0_all_versions(
        dataset: Dataset) -> List[DatasetView]:
    # check for existing
    existing_ancestors = DatasetView.objects.filter(
        dataset=dataset,
        default_type=DatasetView.DefaultViewType.ALL_VERSIONS
    ).exclude(
        default_ancestor_code__isnull=True
    ).values_list('default_ancestor_code', flat=True)
    # find all adm0 in current dataset
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_latest=True,
        is_approved=True
    )
    adm0_entities = entities.values_list('unique_code', flat=True)
    # check for deleted adm0
    for existing in existing_ancestors:
        if existing not in adm0_entities:
            view = DatasetView.objects.filter(
                dataset=dataset,
                default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
                default_ancestor_code=existing
            ).first()
            if view:
                view.delete()
    views = []
    # check for new adm0
    for adm0 in adm0_entities:
        if adm0 not in existing_ancestors:
            entity = entities.filter(
                unique_code=adm0
            ).first()
            adm0_name = entity.label if entity else adm0
            # create new DatasetView
            view_name = f'{dataset.label} - {adm0_name} (All Versions)'
            view_desc = f'{VIEW_ALL_VERSIONS_DESC} for {adm0_name}'
            if dataset.description:
                view_desc = (
                    dataset.description + '. ' +
                    view_desc
                )
            sql = (
                'select gg.* from georepo_geographicalentity gg '
                'left join georepo_geographicalentity ancestor on '
                'ancestor.id=gg.ancestor_id '
                f'where gg.dataset_id={dataset.id} '
                'and gg.is_approved=true '
            )
            sql = (
                sql +
                'AND (('
                'ancestor.id IS NULL '
                f"AND gg.unique_code='{adm0}') "
                'OR ('
                f"ancestor.unique_code='{adm0}'"
                '));'
            )
            dataset_view = DatasetView.objects.create(
                name=view_name,
                description=view_desc,
                dataset=dataset,
                is_static=False,
                query_string=sql,
                default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
                default_ancestor_code=adm0,
                created_by=dataset.created_by
            )
            dataset_view.tags.add(DATASET_VIEW_ALL_VERSIONS_TAG)
            dataset_view.tags.add(DATASET_VIEW_SUBSET_TAG)
            views.append(dataset_view)
            create_sql_view(dataset_view)
    return views


def check_view_exists(view_uuid: str) -> bool:
    sql = (
        'SELECT count(table_name) '
        'FROM information_schema.tables '
        'WHERE table_schema LIKE %s AND '
        'table_type LIKE %s AND '
        'table_name=%s'
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, ['public', 'VIEW', view_uuid])
        total_count = cursor.fetchone()[0]
    return total_count > 0


def create_sql_view(view: DatasetView, **kwargs):
    """
    Create a sql view from dataset view
    :param view: dataset view object
    :return: sql view name
    """
    start = time.time()
    for restricted_command in RESTRICTED_COMMANDS:
        # exclude dataset_id from restricted command
        if restricted_command == 'dataset_id':
            continue
        if f'{restricted_command} ' in view.query_string.lower():
            return False
        if f' {restricted_command} ' in view.query_string.lower():
            return False
        if f' {restricted_command}' in view.query_string.lower():
            return False
        if f' {restricted_command};' in view.query_string.lower():
            return False
    view_name = view.uuid
    query_string = view.query_string
    with connection.cursor() as cursor:
        if '*' in query_string and 'join' in query_string.lower():
            # This is join table, get the first table name
            join_tag = 'join'
            if 'left' in query_string.lower():
                join_tag = 'left'
            if 'right' in query_string.lower():
                join_tag = 'right'
            table_name = re.search(
                r'(\w+\s*)' + join_tag, query_string.lower()
            ).group(1).strip()

            column_names_with_table = []
            cursor.execute(
                "SELECT * FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = N'{view_name}'".format(
                    view_name='georepo_geographicalentity'
                ))
            columns = [col[0] for col in cursor.description]
            col = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
            column_names = [c['column_name'] for c in col]
            for column_name in column_names:
                column_names_with_table.append(
                    f'{table_name}.{column_name}'
                )

            query_string = re.sub(
                'select \*',
                'SELECT {}'.format(','.join(column_names_with_table)),
                query_string,
                flags=re.IGNORECASE)
        if view.is_static:
            drop_sql = (
                'DROP MATERIALIZED VIEW IF EXISTS "{view_name}"'
            ).format(
                view_name=view_name
            )
            cursor.execute('''%s''' % drop_sql)
            sql = (
                'CREATE MATERIALIZED VIEW "{view_name}" '
                'AS {sql_raw}'.format(
                    view_name=view_name,
                    sql_raw=query_string
                )
            )
        else:
            sql = (
                'CREATE OR REPLACE VIEW "{view_name}" AS {sql_raw}'.format(
                    view_name=view_name,
                    sql_raw=query_string
                )
            )
        cursor.execute('''%s''' % sql)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'create_sql_view',
            end - start)
    return view_name


def init_view_privacy_level(view: DatasetView):
    """
    Get max and min privacy level from entities in view
    """
    entities = GeographicalEntity.objects.filter(
        dataset=view.dataset,
        is_approved=True
    )
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(view.uuid))
    # Query existing entities with uuids found in views
    entities = entities.filter(
        id__in=RawSQL(raw_sql, [])
    )
    entities = entities.aggregate(
        Min('privacy_level'),
        Max('privacy_level')
    )
    if (
        entities['privacy_level__max'] is not None and
        entities['privacy_level__min'] is not None
    ):
        view.max_privacy_level = entities['privacy_level__max']
        view.min_privacy_level = entities['privacy_level__min']
        view.save(update_fields=['max_privacy_level', 'min_privacy_level'])


def generate_view_bbox(view: DatasetView):
    """Generate view bbox for each resource."""
    resources = view.datasetviewresource_set.all()
    for resource in resources:
        generate_view_resource_bbox(resource)


def generate_view_resource_bbox(view_resource: DatasetViewResource,
                                **kwargs):
    """
    Generate bbox from view based on privacy level
    """
    start = time.time()
    sql_view = str(view_resource.dataset_view.uuid)
    if not check_view_exists(sql_view):
        return ''
    bbox = []
    geom_col = 'geometry'
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT ST_Extent({geom_col}) as bextent FROM "{sql_view}" '
            f'WHERE privacy_level <= {view_resource.privacy_level} AND '
            'is_approved=True'
        )
        extent = cursor.fetchone()
        if extent:
            try:
                bbox = re.findall(r'[-+]?(?:\d*\.\d+|\d+)', extent[0])
            except TypeError:
                pass
    if bbox:
        _bbox = []
        for coord in bbox:
            _bbox.append(str(round(float(coord), 3)))
        view_resource.bbox = ','.join(_bbox)
        view_resource.save(update_fields=['bbox'])

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'generate_view_resource_bbox',
            end - start)
    return view_resource.bbox


def get_view_tiling_status(view_resource_queryset):
    """Get tiling status of dataset view."""
    # check for error
    error_queryset = view_resource_queryset.filter(
        status=DatasetView.DatasetViewStatus.ERROR
    )
    view_resources = view_resource_queryset.filter(
        entity_count__gt=0
    ).aggregate(
        Avg('vector_tiles_progress')
    )
    tiling_progress = (
        view_resources['vector_tiles_progress__avg'] if
        view_resources['vector_tiles_progress__avg'] else 0
    )
    if error_queryset.exists():
        return 'Error', tiling_progress
    tiling_status = 'Queued'
    if isclose(tiling_progress, 100, abs_tol=1e-4):
        tiling_status = 'Done'
    elif tiling_progress > 0:
        tiling_status = 'Processing'
    return tiling_status, tiling_progress


def get_view_product_status(view_resource_queryset, product=None):
    """Get product status of dataset view."""
    # check for error
    error_queryset = view_resource_queryset.filter(
        status=DatasetView.DatasetViewStatus.ERROR
    )
    field = f'{product}_progress' if product else 'data_product_progress'
    view_resources = view_resource_queryset.aggregate(
        Avg(field)
    )
    product_progress = (
        view_resources[f'{field}__avg'] if
        view_resources[f'{field}__avg'] else 0
    )
    if error_queryset.exists():
        return 'Error', product_progress
    product_status = 'Queued'
    if isclose(product_progress, 100, abs_tol=1e-4):
        product_status = 'Done'
    elif product_progress > 0:
        product_status = 'Processing'
    return product_status, product_progress


def get_entities_count_in_view(
    view: DatasetView,
    privacy_level: int,
    level: int = None,
    **kwargs):
    start = time.time()
    entities = GeographicalEntity.objects.filter(
        dataset=view.dataset,
        is_approved=True
    )
    # raw_sql to view to select id
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(view.uuid))
    # Query existing entities with uuids found in views
    entities = entities.filter(
        id__in=RawSQL(raw_sql, []),
        privacy_level=privacy_level
    )
    if level is not None:
        entities = entities.filter(
            level=level
        )
    entity_count = entities.count()
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'get_entities_count_in_view',
            end - start)
    return entity_count


def get_view_resource_from_view(
        view: DatasetView,
        user_privacy_level: int) -> DatasetViewResource:
    """Return view resource with vector tiles that user can access."""
    resource_level_for_user = view.get_resource_level_for_user(
        user_privacy_level
    )
    resource = view.datasetviewresource_set.filter(
        privacy_level__lte=resource_level_for_user,
        entity_count__gt=0
    ).order_by('-privacy_level').first()
    return resource


def calculate_entity_count_in_view(view: DatasetView):
    view_resources = DatasetViewResource.objects.filter(
        dataset_view=view
    )
    for view_resource in view_resources:
        view_resource.entity_count = (
            get_entities_count_in_view(
                view, view_resource.privacy_level
            )
        )
        view_resource.save(update_fields=['entity_count'])
