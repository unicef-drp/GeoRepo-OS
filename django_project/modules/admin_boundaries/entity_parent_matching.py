import time
from typing import Tuple, List
import json
import logging

from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.contrib.gis.db.models.functions import Intersection, Area
from django.db.models import (
    FloatField, ExpressionWrapper
)
from georepo.models import GeographicalEntity, Dataset
from dashboard.models import (
    LayerUploadSession,
    EntityUploadStatus,
    EntityUploadChildLv1,
    LayerFile,
    EntityTemp
)
from georepo.utils.layers import get_feature_value
from georepo.utils.unique_code import get_latest_revision_number
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)


logger = logging.getLogger(__name__)


def do_search_parent_entity_by_geometry(
    geometry: GEOSGeometry,
    dataset: Dataset,
    **kwargs
) -> Tuple[GeographicalEntity, float]:
    start = time.time()
    max_revision_number = get_latest_revision_number(dataset)
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_approved=True,
        revision_number=max_revision_number,
        geometry__bboverlaps=geometry
    )
    # annotate the overlaps area
    entities = entities.annotate(
        intersect_area=Intersection('geometry', geometry)
    ).annotate(
        overlap_area=ExpressionWrapper(
            Area('intersect_area') / geometry.area,
            output_field=FloatField()
        )
    ).order_by('-overlap_area', 'internal_code')
    entity = entities.first()
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'do_search_parent_entity_by_geometry',
            end - start
        )
    return entity, getattr(entity, 'overlap_area', 0) * 100


def do_search_parent_entity_by_geometry_for_level0(
    geometry: GEOSGeometry,
    layer_file: LayerFile,
    **kwargs
) -> Tuple[EntityTemp, float]:
    start = time.time()
    entities = EntityTemp.objects.filter(
        level=0,
        layer_file=layer_file,
        geometry__bboverlaps=geometry
    )
    # annotate the overlaps area
    entities = entities.annotate(
        intersect_area=Intersection('geometry', geometry)
    ).annotate(
        overlap_area=ExpressionWrapper(
            Area('intersect_area') / geometry.area,
            output_field=FloatField()
        )
    ).order_by('-overlap_area', 'entity_id')
    entity = entities.first()
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'do_search_parent_entity_by_geometry_for_level0',
            end - start
        )
    return entity, getattr(entity, 'overlap_area', 0) * 100


def do_process_layer_files_for_parent_matching(
    upload_session: LayerUploadSession,
    **kwargs
) -> List[EntityUploadStatus]:
    start = time.time()
    # find layer file level 1 from the session
    layer_files = upload_session.layerfile_set.filter(level=1)
    if not layer_files.exists():
        return
    layer_file = layer_files.first()
    total_no_match = 0
    results = []
    temp_entities = EntityTemp.objects.filter(
        upload_session=upload_session,
        layer_file=layer_file
    ).order_by('feature_index')
    total_features = temp_entities.count()
    upload_session.progress = (
        'Auto parent matching admin level 1 entities '
        f'(0/{total_features})'
    )
    upload_session.save(update_fields=['progress'])
    for temp_entity in temp_entities:
        parent_entity_id = temp_entity.parent_entity_id
        # do search
        matched_parent_entity, overlap_percentage = (
            do_search_parent_entity_by_geometry(
                temp_entity.geometry,
                upload_session.dataset,
                **kwargs
            )
        )
        entity_upload = None
        if matched_parent_entity:
            entity_upload, _ = (
                EntityUploadStatus.objects.update_or_create(
                    upload_session=upload_session,
                    original_geographical_entity=matched_parent_entity
                )
            )
            results.append(entity_upload)
        else:
            # nothing is found from parent matching
            total_no_match = total_no_match + 1
        if entity_upload:
            EntityUploadChildLv1.objects.create(
                entity_upload=entity_upload,
                entity_id=temp_entity.entity_id,
                entity_name=temp_entity.entity_name,
                overlap_percentage=overlap_percentage,
                parent_entity_id=temp_entity.parent_entity_id,
                is_parent_rematched=(
                    temp_entity.parent_entity_id !=
                    matched_parent_entity.internal_code
                ),
                feature_index=temp_entity.feature_index
            )
            if temp_entity.parent_entity_id != matched_parent_entity.internal_code:
                # update EntityTemp level 1 and above
                temp_entity.parent_entity_id = matched_parent_entity.internal_code
                temp_entity.ancestor_entity_id = matched_parent_entity.internal_code
                temp_entity.is_parent_rematched = True
                temp_entity.overlap_percentage = overlap_percentage
                temp_entity.save(update_fields=['parent_entity_id',
                                                'ancestor_entity_id',
                                                'is_parent_rematched',
                                                'overlap_percentage'])
                EntityTemp.objects.filter(
                    upload_session=upload_session,
                    level__gt=1,
                    ancestor_entity_id=parent_entity_id
                ).update(
                    ancestor_entity_id=matched_parent_entity.internal_code
                )
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'({temp_entity.feature_index + 1}/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        if temp_entity.feature_index % 20 == 0:
            logger.info(upload_session.progress)
    upload_session.progress = (
        'Auto parent matching admin level 1 entities '
        f'({total_features}/{total_features})'
    )
    upload_session.save(update_fields=['progress'])
    logger.info(upload_session.progress)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'admin_boundaries.upload_preprocessing.prepare_validation',
            end - start
        )
    return results


def do_process_layer_files_for_parent_matching_level0(
    upload_session: LayerUploadSession,
    entity_uploads: List[EntityUploadStatus],
    **kwargs
):
    start = time.time()
    # find layer file level 0
    layer_files0 = upload_session.layerfile_set.filter(level=0)
    if not layer_files0.exists():
        return
    layer_file0 = layer_files0.first()
    # find layer file level 1 from the session
    layer_files = upload_session.layerfile_set.filter(level=1)
    if not layer_files.exists():
        return
    layer_file = layer_files.first()
    total_no_match = 0
    temp_entities = EntityTemp.objects.filter(
        upload_session=upload_session,
        layer_file=layer_file
    ).order_by('feature_index')
    total_features = temp_entities.count()
    upload_session.progress = (
        'Auto parent matching admin level 1 entities '
        f'(0/{total_features})'
    )
    upload_session.save(update_fields=['progress'])
    for temp_entity in temp_entities:
        parent_entity_id = temp_entity.parent_entity_id
        # do search
        matched_parent_entity, overlap_percentage = (
            do_search_parent_entity_by_geometry_for_level0(
                temp_entity.geometry,
                layer_file0,
                **kwargs
            )
        )
        entity_upload = None
        if matched_parent_entity:
            # find matched_parent_entity from entity_uploads
            entity_upload = find_matched_entity_upload(
                entity_uploads,
                matched_parent_entity
            )
        else:
            # nothing is found from parent matching
            total_no_match = total_no_match + 1
        if entity_upload:
            EntityUploadChildLv1.objects.create(
                entity_upload=entity_upload,
                entity_id=temp_entity.entity_id,
                entity_name=temp_entity.entity_name,
                overlap_percentage=overlap_percentage,
                parent_entity_id=temp_entity.parent_entity_id,
                is_parent_rematched=(
                    temp_entity.parent_entity_id !=
                    matched_parent_entity.entity_id
                ),
                feature_index=temp_entity.feature_index
            )
            if temp_entity.parent_entity_id != matched_parent_entity.entity_id:
                # update EntityTemp level 1 and above
                temp_entity.parent_entity_id = matched_parent_entity.entity_id
                temp_entity.ancestor_entity_id = matched_parent_entity.entity_id
                temp_entity.is_parent_rematched = True
                temp_entity.overlap_percentage = overlap_percentage
                temp_entity.save(update_fields=['parent_entity_id',
                                                'ancestor_entity_id',
                                                'is_parent_rematched',
                                                'overlap_percentage'])
                EntityTemp.objects.filter(
                    upload_session=upload_session,
                    level__gt=1,
                    ancestor_entity_id=parent_entity_id
                ).update(
                    ancestor_entity_id=matched_parent_entity.entity_id
                )
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'({temp_entity.feature_index + 1}/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        if temp_entity.feature_index % 20 == 0:
            logger.info(upload_session.progress)
    upload_session.progress = (
        'Auto parent matching admin level 1 entities '
        f'({total_features}/{total_features})'
    )
    upload_session.save(update_fields=['progress'])
    logger.info(upload_session.progress)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'do_process_layer_files_for_parent_matching_level0',
            end - start
        )


def find_matched_entity_upload(entity_uploads: List[EntityUploadStatus],
                               entity: EntityTemp):
    for upload in entity_uploads:
        entity_id = (
            upload.original_geographical_entity.internal_code if
            upload.original_geographical_entity else
            upload.revised_entity_id
        )
        if entity_id == entity.entity_id:
            return upload
    return None
