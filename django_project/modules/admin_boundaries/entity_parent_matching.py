from typing import Tuple, List
import json
import fiona
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
from dashboard.models.layer_file import (
    SHAPEFILE
)
from georepo.utils.layers import get_feature_value
from georepo.utils.unique_code import get_latest_revision_number

logger = logging.getLogger(__name__)


def do_search_parent_entity_by_geometry(
        geometry: GEOSGeometry,
        dataset: Dataset) -> Tuple[GeographicalEntity, float]:
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
    return entity, getattr(entity, 'overlap_area', 0) * 100


def do_search_parent_entity_by_geometry_for_level0(
        geometry: GEOSGeometry,
        dataset: Dataset,
        layer_file: LayerFile) -> Tuple[GeographicalEntity, float]:
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
    return entity, getattr(entity, 'overlap_area', 0) * 100


def do_process_layer_files_for_parent_matching(
        upload_session: LayerUploadSession) -> List[EntityUploadStatus]:
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
    layer_file_path = layer_file.layer_file.path
    if layer_file.layer_type == SHAPEFILE:
        layer_file_path = f'zip://{layer_file.layer_file.path}'
    with fiona.open(layer_file_path, encoding='utf-8') as features:
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
                    upload_session.dataset
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
    return results


def do_process_layer_files_for_parent_matching_level0(
        upload_session: LayerUploadSession,
        entity_uploads: List[EntityUploadStatus]):
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
    layer_file_path = layer_file.layer_file.path
    if layer_file.layer_type == SHAPEFILE:
        layer_file_path = f'zip://{layer_file.layer_file.path}'
    with fiona.open(layer_file_path, encoding='utf-8') as features:
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
                    layer_file0
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
