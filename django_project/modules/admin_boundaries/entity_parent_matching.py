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
    LayerFile
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
    dataset: Dataset,
    layer_file: LayerFile,
    **kwargs
) -> Tuple[GeographicalEntity, float]:
    start = time.time()
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        level=0,
        is_approved=False,
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
    ).order_by('-overlap_area', 'internal_code')
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
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    name_field = (
        [name_field['field'] for name_field in layer_file.name_fields
            if name_field['default']][0]
    )
    total_no_match = 0
    results = []
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as features:
        total_features = len(features)
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'(0/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        for feature_idx, feature in enumerate(features):
            parent_entity_id = (
                get_feature_value(feature, layer_file.parent_id_field, None)
            )
            # default code, should pass even if empty
            entity_id = (
                get_feature_value(feature, id_field)
            )
            entity_name = (
                get_feature_value(feature, name_field)
            )
            # create geometry
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            # do search
            matched_parent_entity, overlap_percentage = (
                do_search_parent_entity_by_geometry(
                    geom,
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
                    entity_id=entity_id,
                    entity_name=entity_name,
                    overlap_percentage=overlap_percentage,
                    parent_entity_id=parent_entity_id,
                    is_parent_rematched=(
                        parent_entity_id !=
                        matched_parent_entity.internal_code
                    ),
                    feature_index=feature_idx
                )
            upload_session.progress = (
                'Auto parent matching admin level 1 entities '
                f'({feature_idx + 1}/{total_features})'
            )
            upload_session.save(update_fields=['progress'])
            if feature_idx % 20 == 0:
                logger.info(upload_session.progress)
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'({total_features}/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        logger.info(upload_session.progress)
        delete_tmp_shapefile(features.path)
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
    id_field = (
        [id_field['field'] for id_field in layer_file.id_fields
            if id_field['default']][0]
    )
    name_field = (
        [name_field['field'] for name_field in layer_file.name_fields
            if name_field['default']][0]
    )
    total_no_match = 0
    with open_collection_by_file(layer_file.layer_file,
                                 layer_file.layer_type) as features:
        total_features = len(features)
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'(0/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        for feature_idx, feature in enumerate(features):
            parent_entity_id = (
                get_feature_value(feature, layer_file.parent_id_field, None)
            )
            # default code, should pass even if empty
            entity_id = (
                get_feature_value(feature, id_field)
            )
            entity_name = (
                get_feature_value(feature, name_field)
            )
            # create geometry
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            # do search
            matched_parent_entity, overlap_percentage = (
                do_search_parent_entity_by_geometry_for_level0(
                    geom,
                    upload_session.dataset,
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
                    entity_id=entity_id,
                    entity_name=entity_name,
                    overlap_percentage=overlap_percentage,
                    parent_entity_id=parent_entity_id,
                    is_parent_rematched=(
                        parent_entity_id !=
                        matched_parent_entity.internal_code
                    ),
                    feature_index=feature_idx
                )
            upload_session.progress = (
                'Auto parent matching admin level 1 entities '
                f'({feature_idx + 1}/{total_features})'
            )
            upload_session.save(update_fields=['progress'])
            if feature_idx % 20 == 0:
                logger.info(upload_session.progress)
        upload_session.progress = (
            'Auto parent matching admin level 1 entities '
            f'({total_features}/{total_features})'
        )
        upload_session.save(update_fields=['progress'])
        logger.info(upload_session.progress)
        delete_tmp_shapefile(features.path)
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'do_process_layer_files_for_parent_matching_level0',
            end - start
        )


def find_matched_entity_upload(entity_uploads: List[EntityUploadStatus],
                               entity: GeographicalEntity):
    for upload in entity_uploads:
        entity_id = (
            upload.original_geographical_entity.internal_code if
            upload.original_geographical_entity else
            upload.revised_entity_id
        )
        if entity_id == entity.internal_code:
            return upload
    return None
