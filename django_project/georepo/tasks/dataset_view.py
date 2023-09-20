from celery import shared_task
from django.db import connection
from django.db.models import Q
from georepo.models.entity import GeographicalEntity

from georepo.models.dataset_view import (
    DatasetView
)


@shared_task(name="check_affected_views")
def check_affected_dataset_views(
    entity_id: int = None,
    entity_ids=[]
):
    """
    Trigger checking affected views for entity update or revision approve.
    """
    # Query Views that are synced and dynamic
    views_to_check = DatasetView.objects.filter(
        is_static=False
    ).filter(
        Q(vector_tile_sync_status=DatasetView.SyncStatus.SYNCED) |
        Q(product_sync_status=DatasetView.SyncStatus.SYNCED)
    )
    if entity_ids:
        entity_ids = tuple(
            GeographicalEntity.objects.filter(
                unique_code__in=entity_ids
            ).values_list('id', flat=True)
        )

    for view in views_to_check:
        if entity_id:
            raw_sql = (
                'select count(*) from "{}" where id={} or ancestor_id={};'
            ).format(
                view.uuid,
                entity_id,
                entity_id
            )
        elif entity_ids:
            raw_sql = (
                'select count(*) from "{}" where '
                'id in {} or ancestor_id in {};'
            ).format(
                view.uuid,
                entity_ids,
                entity_ids
            )
        with connection.cursor() as cursor:
            cursor.execute(
                raw_sql
            )
            total_count = cursor.fetchone()[0]
            print(total_count)
            if total_count > 0:
                view.set_out_of_sync(
                    tiling_config=False,
                    vector_tile=True,
                    product=True
                )
