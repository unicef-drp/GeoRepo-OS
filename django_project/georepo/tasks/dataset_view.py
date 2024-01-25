from typing import List
import traceback
import logging
from celery import shared_task
from django.db import connection
from django.db.models import Q
from georepo.models.entity import GeographicalEntity

from georepo.models import (
    DatasetView, DatasetViewResource,
    ExportRequest, GEOJSON_EXPORT_TYPE,
    KML_EXPORT_TYPE, TOPOJSON_EXPORT_TYPE,
    SHAPEFILE_EXPORT_TYPE, ExportRequestStatusText
)
from georepo.models.base_task_request import ERROR
from georepo.utils.celery_helper import cancel_task
from georepo.utils.exporter_base import DatasetViewExporterBase
from georepo.utils.geojson import GeojsonViewExporter
from georepo.utils.shapefile import ShapefileViewExporter
from georepo.utils.kml import KmlViewExporter
from georepo.utils.topojson import TopojsonViewExporter


logger = logging.getLogger(__name__)


@shared_task(name="check_affected_views")
def check_affected_dataset_views(
    dataset_id: int,
    entity_id: List[int] = [],
    unique_codes = [],
    is_geom_changed: bool = True
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
    if entity_id:
        entity_id = tuple(entity_id)
        entity_id = str(entity_id)
        if entity_id[-2] == ',':
            entity_id = entity_id[:-2] + entity_id[-1]

    for view in views_to_check.iterator(chunk_size=1):
        if entity_id:
            raw_sql = (
                'select count(*) from "{}" where '
                'id in {} or ancestor_id in {};'
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
                if (
                    is_geom_changed and
                    not view.datasetviewtilingconfig_set.all().exists()
                ):
                    # update dataset simplification to out of sync
                    view.dataset.sync_status = (
                        DatasetView.SyncStatus.OUT_OF_SYNC
                    )
                    view.dataset.simplification_sync_status = (
                        DatasetView.SyncStatus.OUT_OF_SYNC
                    )
                    view.dataset.is_simplified = False
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
    for view in views_to_check.iterator(chunk_size=1):
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


def try_clear_temp_resource_on_error(exporter: DatasetViewExporterBase):
    try:
        exporter.do_remove_temp_dir()
    except Exception:
        pass


@shared_task(name="dataset_view_exporter")
def dataset_view_exporter(request_id):
    request = ExportRequest.objects.get(id=request_id)
    exporter = None
    if request.format == GEOJSON_EXPORT_TYPE:
        exporter = GeojsonViewExporter(request)
    elif request.format == SHAPEFILE_EXPORT_TYPE:
        exporter = ShapefileViewExporter(request)
    elif request.format == KML_EXPORT_TYPE:
        exporter = KmlViewExporter(request)
    elif request.format == TOPOJSON_EXPORT_TYPE:
        exporter = TopojsonViewExporter(request)
    if exporter is None:
        request.errors = f'Unknown export format: {request.format}'
        request.status = ERROR
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.save(update_fields=['errors', 'status', 'status_text'])
        return
    try:
        exporter.init_exporter()
        exporter.run()
    except Exception as ex:
        logger.error('Failed Process DatasetView Exporter!')
        logger.error(ex)
        logger.error(traceback.format_exc())
        request.status = ERROR
        request.errors = str(ex)
        request.task_id = None
        request.status_text = str(ExportRequestStatusText.ABORTED)
        request.save(update_fields=[
            'status', 'errors', 'task_id', 'status_text'])
        try_clear_temp_resource_on_error(exporter)
