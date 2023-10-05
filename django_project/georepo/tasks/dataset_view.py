from celery import shared_task
from django.db import connection
from django.db.models import Q
from georepo.models.entity import GeographicalEntity

from georepo.models import (
    DatasetView, DatasetViewResource
)
from georepo.utils.celery_helper import cancel_task


@shared_task(name="check_affected_views")
def check_affected_dataset_views(
    dataset_id: int,
    entity_id: int = None,
    unique_codes=[]
):
    """
    Trigger checking affected views for entity update or revision approve.
    """
    # Query Views that are synced and dynamic
    views_to_check = DatasetView.objects.filter(
        dataset_id=dataset_id,
        is_static=False
    ).filter(
        Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCING) |
        Q(simplification_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(simplification_sync_status=DatasetView.SyncStatus.SYNCING) |
        Q(product_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(product_sync_status=DatasetView.SyncStatus.SYNCING)
    )
    if unique_codes:
        unique_codes = tuple(
            GeographicalEntity.objects.filter(
                dataset_id=dataset_id,
                unique_code__in=unique_codes
            ).values_list('id', flat=True)
        )
        unique_codes = str(unique_codes)
        if unique_codes[-2] == ',':
            unique_codes = unique_codes[:-2] + unique_codes[-1]

    for view in views_to_check:
        if entity_id:
            raw_sql = (
                'select count(*) from "{}" where id={} or ancestor_id={};'
            ).format(
                view.uuid,
                entity_id,
                entity_id
            )
        elif unique_codes:
            raw_sql = (
                'select count(*) from "{}" where '
                'id in {} or ancestor_id in {};'
            ).format(
                view.uuid,
                unique_codes,
                unique_codes
            )
        with connection.cursor() as cursor:
            cursor.execute(
                raw_sql
            )
            total_count = cursor.fetchone()[0]
            if total_count > 0:
                # cancel ongoing task
                if view.simplification_task_id:
                    cancel_task(view.simplification_task_id)
                if view.task_id:
                    cancel_task(view.task_id)
                view_resources = DatasetViewResource.objects.filter(
                    dataset_view=view
                )
                for view_resource in view_resources:
                    if view_resource.vector_tiles_task_id:
                        cancel_task(view_resource.vector_tiles_task_id)
                    if view_resource.product_task_id:
                        cancel_task(view_resource.product_task_id)
                view.set_out_of_sync(
                    tiling_config=False,
                    vector_tile=True,
                    product=True,
                    skip_signal=False
                )
                view.dataset.sync_status = DatasetView.SyncStatus.OUT_OF_SYNC
                view.dataset.save()


@shared_task(name="check_affected_views_from_tiling_config")
def check_affected_views_from_tiling_config(
    dataset_id: int
):
    """
    Trigger checking affected views for dataset tiling config update.
    """
    views_to_check = DatasetView.objects.filter(
        dataset_id=dataset_id
    ).filter(
        Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCING) |
        Q(simplification_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(simplification_sync_status=DatasetView.SyncStatus.SYNCING)
    )
    for view in views_to_check:
        if view.datasetviewtilingconfig_set.all().exists():
            continue
        # cancel ongoing task
        if view.simplification_task_id:
            cancel_task(view.simplification_task_id)
        if view.task_id:
            cancel_task(view.task_id)
        view_resources = DatasetViewResource.objects.filter(
            dataset_view=view
        )
        for view_resource in view_resources:
            if view_resource.vector_tiles_task_id:
                cancel_task(view_resource.vector_tiles_task_id)
        view.set_out_of_sync(
            tiling_config=True,
            vector_tile=True,
            product=False
        )
