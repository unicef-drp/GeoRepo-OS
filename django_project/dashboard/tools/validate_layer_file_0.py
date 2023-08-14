from typing import Tuple, List
import fiona
import json
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon

from georepo.models import (
    GeographicalEntity, EntityType
)
from georepo.validation.layer_validation import (
    retrieve_layer0_default_codes
)
from georepo.utils.unique_code import get_latest_revision_number
from dashboard.models import (
    LayerUploadSession, EntityUploadStatus
)
from dashboard.models.layer_file import (
    SHAPEFILE
)


def validate_layer_file_0(
        upload_session: LayerUploadSession) -> Tuple[bool, str]:
    """
    Return True, None if all entity in layer file 0 has unique default code
    else return False, duplicateDefaultCode.
    create_temp_entity = Generate temporary entities for admin level 0
    for auto parent matching. This parameter value may be False if there is no
    admin level 1 uploads.
    """
    # find layer file level 0 from the session
    layer_files = upload_session.layerfile_set.filter(level=0)
    if not layer_files.exists():
        # ignore if no layer file 0 exists
        return True
    layer_file_0 = layer_files.first()
    id_field = (
        [id_field['field'] for id_field in layer_file_0.id_fields
            if id_field['default']][0]
    )
    layer0_default_codes = []
    is_valid = True
    duplicate_code = None
    layer_file_path = layer_file_0.layer_file.path
    if layer_file_0.layer_type == SHAPEFILE:
        layer_file_path = f'zip://{layer_file_0.layer_file.path}'
    with fiona.open(layer_file_path, encoding='utf-8') as features:
        for feature in features:
            # default code
            entity_id = (
                str(feature['properties'][id_field]) if
                id_field in feature['properties'] else None
            )
            if not entity_id:
                # skip if entity_id not found
                continue
            if entity_id in layer0_default_codes:
                is_valid = False
                duplicate_code = entity_id
                break
            layer0_default_codes.append(entity_id)
    return is_valid, duplicate_code


def preprocess_layer_file_0(
        upload_session: LayerUploadSession,
        create_temp_entity_level0: bool = False) -> List[EntityUploadStatus]:
    """
    Read layer files level 0 and create entity uploads object
    """
    level_0_data = retrieve_layer0_default_codes(upload_session)
    max_revision_number = get_latest_revision_number(upload_session.dataset)
    entities = GeographicalEntity.objects.filter(
        dataset=upload_session.dataset,
        level=0,
        is_approved=True,
        revision_number=max_revision_number
    ).order_by('uuid').distinct('uuid')
    results = []
    # merge level_0_data from layer_file with existing level0 data
    for entity in entities:
        layer0 = (
            [(layer0, idx) for idx, layer0 in
                enumerate(level_0_data)
                if layer0['layer0_id'] == entity.internal_code]
        )
        if layer0:
            entity_upload, _ = (
                EntityUploadStatus.objects.update_or_create(
                    upload_session=upload_session,
                    original_geographical_entity=entity
                )
            )
            results.append(entity_upload)
            del level_0_data[layer0[0][1]]
    for layer0 in level_0_data:
        if layer0['layer0_id']:
            entity_upload, _ = (
                EntityUploadStatus.objects.update_or_create(
                    upload_session=upload_session,
                    revised_entity_id=layer0['layer0_id'],
                    revised_entity_name=layer0['country']
                )
            )
            results.append(entity_upload)
    if create_temp_entity_level0:
        create_temp_admin_level_0(upload_session)
    return results


def create_temp_admin_level_0(upload_session: LayerUploadSession):
    """
    Entities admin level 0 may be generated when auto parent matching
    during upload level 0
    """
    entity_type = EntityType.objects.all().first()
    if not entity_type:
        entity_type = EntityType.objects.get_by_label(
            'Country'
        )
    # find layer file level 0 from the session
    layer_files = upload_session.layerfile_set.filter(level=0)
    if not layer_files.exists():
        # ignore if no layer file 0 exists
        return
    layer_file_0 = layer_files.first()
    id_field = (
        [id_field['field'] for id_field in layer_file_0.id_fields
            if id_field['default']][0]
    )
    layer0_default_codes = []
    layer_file_path = layer_file_0.layer_file.path
    if layer_file_0.layer_type == SHAPEFILE:
        layer_file_path = f'zip://{layer_file_0.layer_file.path}'
    with fiona.open(layer_file_path, encoding='utf-8') as features:
        for feature in features:
            # default code
            entity_id = (
                str(feature['properties'][id_field]) if
                id_field in feature['properties'] else None
            )
            if not entity_id:
                # skip if entity_id not found
                continue
            if entity_id in layer0_default_codes:
                continue
            layer0_default_codes.append(entity_id)
            geom_str = json.dumps(feature['geometry'])
            geom = GEOSGeometry(geom_str)
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            # create entity level 0 temporary to do parent matching
            GeographicalEntity.objects.create(
                level=0,
                internal_code=entity_id,
                layer_file=layer_file_0,
                dataset=upload_session.dataset,
                type=entity_type,
                geometry=geom,
                is_approved=False,
                is_validated=False,
                is_latest=False
            )


def remove_temp_admin_level_0(upload_session: LayerUploadSession):
    """
    This function is to remove entities admin level 0 may be generated
    when auto parent matching during upload level 0.
    """
    layer_files0 = upload_session.layerfile_set.filter(level=0)
    if layer_files0.exists():
        layer_file0 = layer_files0.first()
        temp_entities = GeographicalEntity.objects.filter(
            dataset=upload_session.dataset,
            level=0,
            is_approved=False,
            layer_file=layer_file0
        )
        temp_entities.delete()
