from typing import Tuple
import csv
import json
import uuid
from io import StringIO
import logging
import traceback
import time

from core.celery import app

from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import IntegerField, Max
from django.db.models.functions import Cast

from dashboard.models import LayerFile, ERROR
from dashboard.models.entity_upload import EntityUploadStatus, VALID, \
    EntityUploadChildLv1, EntityTemp, WARNING, IMPORTABLE_UPLOAD_STATUS_LIST
from dashboard.models.layer_upload_session import LayerUploadSession
from georepo.models.entity import GeographicalEntity, EntityType, EntityName,\
    EntityId
from modules.admin_boundaries.error_type import (
    ErrorType,
    LEVEL,
    ERROR_CHECK,
    ENTITY_CODE,
    ENTITY_NAME,
    create_layer_error,
    create_level_error_report,
    ALLOWABLE_ERROR_TYPES,
    SUPERADMIN_BYPASS_ERROR
)
from georepo.utils.layers import check_valid_value, get_feature_value
from modules.admin_boundaries.geometry_checker import (
    self_contact_check,
    duplicate_nodes_check,
    duplicate_check,
    contained_check,
    hierarchy_check,
    overlap_check,
    gap_check,
    valid_nodes_check,
    self_intersects_check_with_flag
)
from georepo.utils.fiona_utils import (
    open_collection_by_file,
    delete_tmp_shapefile
)
from georepo.utils.mapshaper import simplify_for_dataset

logger = logging.getLogger(__name__)


def do_self_intersects_check(geom: GEOSGeometry,
                             internal_code: str,
                             entity_upload: EntityUploadStatus,
                             **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        # upload_session: LayerUploadSession = entity_upload.upload_session
        # tolerance = upload_session.tolerance
        # errors = self_intersects_check(geom, tolerance)
        # is_valid = len(errors) == 0

        is_valid, _, _ = self_intersects_check_with_flag(geom)
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on self_intersects_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'self_intersects_check {(end - start)} seconds')

    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_self_intersects_check',
            end - start)
    return is_valid


def do_self_contact_check(geom: GEOSGeometry,
                          internal_code: str,
                          entity_upload: EntityUploadStatus,
                          **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        upload_session: LayerUploadSession = entity_upload.upload_session
        tolerance = upload_session.tolerance
        errors = self_contact_check(geom, tolerance)
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on self_contact_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'self_contact_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_self_contact_check',
            end - start)
    return is_valid


def do_duplicate_nodes_check(geom: GEOSGeometry,
                             internal_code: str,
                             entity_upload: EntityUploadStatus,
                             **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        upload_session: LayerUploadSession = entity_upload.upload_session
        tolerance = upload_session.tolerance
        errors = duplicate_nodes_check(geom, tolerance)
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on duplicate_nodes_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'duplicate_nodes_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_duplicate_nodes_check',
            end - start)
    return is_valid


def do_duplicate_check(geom: GEOSGeometry,
                       internal_code: str,
                       entity_upload: EntityUploadStatus,
                       layer_file: LayerFile,
                       **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        other_geoms = GeographicalEntity.objects.filter(
            layer_file=layer_file
        )
        errors, geom_error = duplicate_check(geom, internal_code, other_geoms)
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on duplicate_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'duplicate_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_duplicate_check',
            end - start)
    return is_valid


def do_hierarchy_check(geom: GEOSGeometry,
                       internal_code: str,
                       entity_upload: EntityUploadStatus,
                       parent: GeographicalEntity,
                       **kwargs) -> bool:
    if parent is None:
        return True
    start = time.time()
    try:
        errors, geom_error = hierarchy_check(
            geom,
            internal_code,
            parent.geometry
        )
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on hierarchy_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'hierarchy_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_hierarchy_check',
            end - start)
    return is_valid


def do_contained_check(entity: GeographicalEntity,
                       entity_upload: EntityUploadStatus,
                       layer_file: LayerFile,
                       **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        other_geoms = GeographicalEntity.objects.filter(
            layer_file=layer_file
        ).exclude(
            id=entity.id
        )
        errors, geom_error = contained_check(
            entity.geometry,
            entity.internal_code,
            other_geoms
        )
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on contained_check'
            f'{entity.internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'contained_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_contained_check',
            end - start)
    return is_valid


def do_overlap_check(geom: GEOSGeometry,
                     internal_code: str,
                     entity_upload: EntityUploadStatus,
                     layer_file: LayerFile,
                     **kwargs) -> bool:
    is_valid = False
    start = time.time()
    try:
        upload_session: LayerUploadSession = entity_upload.upload_session
        tolerance = upload_session.tolerance
        overlap_threshold_map_units = upload_session.overlaps_threshold
        other_geoms = GeographicalEntity.objects.filter(
            layer_file=layer_file
        )
        errors, geom_error = overlap_check(
            geom,
            other_geoms,
            tolerance,
            overlap_threshold_map_units
        )
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on overlap_check'
            f'{internal_code} = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'overlap_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_overlap_check',
            end - start)
    return is_valid


def do_gap_check(entity_upload: EntityUploadStatus,
                 layer_file: LayerFile,
                 level: int,
                 **kwargs):
    is_valid = False
    errors = []
    start = time.time()
    try:
        upload_session: LayerUploadSession = entity_upload.upload_session
        tolerance = upload_session.tolerance
        gap_threshold_map_units = upload_session.gaps_threshold
        geoms = GeographicalEntity.objects.filter(
            dataset=upload_session.dataset,
            layer_file=layer_file,
            level=level,
            ancestor=entity_upload.revised_geographical_entity
        )
        errors, geom_error = gap_check(
            geoms,
            tolerance,
            gap_threshold_map_units
        )
        is_valid = len(errors) == 0
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
        is_valid = False
        if entity_upload.logs is None:
            entity_upload.logs = ''
        entity_upload.logs += (
            f'\nException {type(ex)} on gap_check'
            f' = {str(ex)}'
        )
        entity_upload.save(update_fields=['logs'])
    end = time.time()
    logger.debug(f'gap_check {(end - start)} seconds')
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_gap_check',
            end - start)
    return is_valid, errors


def do_valid_nodes_check(geom_str: str,
                         internal_code: str,
                         entity_upload: EntityUploadStatus,
                         **kwargs):
    geom, error = valid_nodes_check(geom_str, internal_code)
    start = time.time()
    if error:
        entity_upload.logs += (
            f'\nException on valid_nodes_check'
            f'{internal_code} = {str(error.error)}'
        )
        entity_upload.save(update_fields=['logs'])

    end = time.time()
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.do_valid_nodes_check',
            end - start)
    return geom


def get_temp_entity_count(upload_session: LayerUploadSession, level: int,
                          ancestor_id: str):
    if level == 0:
        return 1
    return EntityTemp.objects.filter(
        upload_session=upload_session,
        level=level,
        ancestor_entity_id=ancestor_id
    ).count()


def run_validation(entity_upload: EntityUploadStatus, **kwargs) -> bool:
    """
    Validate all layer_files from upload session against
    original geographical entity,
    then create a new revised geographical entity
    :param entity_upload: EntityUpload objects
    :return: boolean status whether the process is successful or not
    """
    logger.info(f'validate admin_boundaries {entity_upload.id}')
    start = time.time()
    layer_files = LayerFile.objects.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(
        layer_upload_session=entity_upload.upload_session
    ).order_by('level_int')
    if (entity_upload.max_level and entity_upload.max_level != '-1'):
        layer_files = layer_files.filter(
            level_int__lte=int(entity_upload.max_level)
        )

    revision = 1
    dataset = entity_upload.upload_session.dataset
    if entity_upload.original_geographical_entity:
        # to find revision number for an upload,
        # find maximum revision number for given level 0 entity
        max_revision = GeographicalEntity.objects.filter(
            dataset=dataset,
            is_approved=True
        ).aggregate(Max('revision_number'))['revision_number__max']
        if max_revision:
            revision = max_revision + 1

    if (
        not entity_upload.revised_geographical_entity and
            entity_upload.original_geographical_entity
    ):
        # cloned admin level 0 to new revision
        revised = entity_upload.original_geographical_entity
        revised.pk = None
        revised.save()
        revised.is_validated = False
        revised.is_approved = None
        revised.approved_by = None
        if entity_upload.upload_session.is_historical_upload:
            revised.start_date = (
                entity_upload.upload_session.historical_start_date
            )
            revised.end_date = (
                entity_upload.upload_session.historical_end_date
            )
        else:
            revised.start_date = entity_upload.upload_session.started_at
            revised.end_date = None
        revised.revision_number = revision
        revised.uuid_revision = str(uuid.uuid4())
        if not revised.admin_level_name:
            revised.admin_level_name = (
                entity_upload.get_entity_admin_level_name(0)
            )
        revised.unique_code_version = None
        revised.save()
        entity_upload.revised_geographical_entity = revised
        entity_upload.revision_number = revision
        entity_upload.save()

    ancestor = (
        entity_upload.revised_geographical_entity
        if entity_upload.revised_geographical_entity else None
    )

    if ancestor and not ancestor.is_approved:
        children = ancestor.all_children()
        is_upload_level_0 = layer_files.filter(
            level_int=0
        ).exists()
        if is_upload_level_0:
            # remove revised from current entity upload so can be deleted
            entity_upload.revised_geographical_entity = None
            entity_upload.save()
        else:
            children = children.exclude(id=ancestor.id)
        children.delete()

    validation_summaries = []
    error_summaries = []

    # fetch included child level 1 for this entity upload
    # this can be from auto parent matching or manually rematched
    children_lv1 = EntityUploadChildLv1.objects.filter(
        entity_upload=entity_upload
    )

    for layer_file in layer_files:
        level = int(layer_file.level)
        admin_level_name = entity_upload.get_entity_admin_level_name(level)

        if level > 0 and not ancestor:
            continue

        level_error_report = create_level_error_report(
            level,
            'Entity',
            ancestor.label if ancestor else entity_upload.revised_entity_name
        )
        with open_collection_by_file(layer_file.layer_file,
                                     layer_file.layer_type) as layer:
            internal_code = ''

            # Check parent entities
            parent_entities = None
            parent_entities_codes = []
            total_features = 1
            if level > 0 and ancestor:
                parent_level = level - 1
                if (
                    entity_upload.revised_geographical_entity.level ==
                        parent_level
                ):
                    parent_entities = GeographicalEntity.objects.filter(
                        id=ancestor.id
                    )
                else:
                    parent_entities = GeographicalEntity.objects.filter(
                        ancestor=ancestor,
                        level=parent_level,
                        dataset=entity_upload.upload_session.dataset,
                        revision_number=revision
                    )
                total_features = get_temp_entity_count(
                    entity_upload.upload_session,
                    level,
                    ancestor.internal_code
                )
            if parent_entities:
                parent_entities_codes = parent_entities.values_list(
                    'internal_code', flat=True
                )

            entity_upload.progress = (
                f'Level {level} - Validation Checks '
                f'(1 of {total_features} polygons)'
            )
            entity_upload.save(update_fields=['progress'])
            layer_index = 0
            feature_included_idx = 0
            for feature_idx, feature in enumerate(layer):
                layer_index += 1
                error_found = False
                layer_error = create_layer_error(level)

                feature_properties = feature['properties']

                # This is a new data, check by the id of the entity
                if level == 0:
                    id_field_found = False
                    level0_entity_id = (
                        entity_upload
                        .original_geographical_entity.internal_code
                        if entity_upload.original_geographical_entity
                        else str(entity_upload.revised_entity_id)
                    )
                    for id_field in layer_file.id_fields:
                        if id_field['default']:
                            internal_code = get_feature_value(
                                feature,
                                id_field['field']
                            )
                            if internal_code == level0_entity_id:
                                id_field_found = True
                                break
                    if not id_field_found:
                        continue

                if feature_idx % 500 == 0:
                    logger.debug(f'Validating Level {level} - '
                                 f'Index {layer_index}')

                feature_parent_code = ''
                parent = None
                if level == 0:
                    parent = None
                else:
                    feature_parent_code = (
                        get_feature_value(
                            feature, layer_file.parent_id_field
                        )
                    )
                    # if level 1 and EntityUploadChildLv1 exists,
                    # then check whether this feature is included
                    is_feature_included = False
                    if (level == 1 and children_lv1.exists()):
                        # check feature included using index
                        # instead of default code, since default code
                        # may be empty at this stage
                        is_feature_included = (
                            children_lv1.filter(
                                feature_index=feature_idx
                            ).exists()
                        )
                        if is_feature_included and parent is None:
                            # if parent is none then use
                            # from revised entity
                            parent = (
                                entity_upload.revised_geographical_entity
                                if entity_upload.
                                revised_geographical_entity else None
                            )
                    else:
                        try:
                            parent = parent_entities.get(
                                internal_code=feature_parent_code,
                                is_approved=None,
                                is_validated=False
                            )
                        except GeographicalEntity.DoesNotExist:
                            pass
                        except GeographicalEntity.MultipleObjectsReturned:
                            duplicates = parent_entities.filter(
                                internal_code=feature_parent_code,
                                is_approved=None,
                                is_validated=False
                            ).order_by('-id')
                            parent = duplicates.first()
                            duplicates.exclude(id=parent.id).delete()
                        # skip if parent is not found
                        # NOTE: PARENT_CODE_HIERARCHY cannot be detected
                        # by current logic, because reading the feature
                        # is using parent code hierarchy
                        is_feature_included = parent is not None
                    if not is_feature_included:
                        continue

                    # Parent id fields
                    is_valid_parent_id_field = (
                        check_valid_value(feature, layer_file.parent_id_field)
                    )
                    if not is_valid_parent_id_field:
                        layer_error[
                            ErrorType.PARENT_ID_FIELD_ERROR.value] = (
                                ERROR_CHECK
                        )
                        level_error_report[
                            ErrorType.PARENT_ID_FIELD_ERROR.value] += 1

                entity_upload.progress = (
                    f'Level {level} - Validation Checks '
                    f'({feature_included_idx + 1} of '
                    f'{total_features} polygons)'
                )
                entity_upload.save(update_fields=['progress'])
                # Check name fields
                name_fields = []
                label = '-'
                for name_field_idx, name_field in enumerate(
                    layer_file.name_fields
                ):
                    name_field_value = (
                        get_feature_value(feature, name_field['field'])
                    )
                    if name_field['default']:
                        # if default name, then validate the value
                        label = name_field_value
                        layer_error[ENTITY_NAME] = (
                            label
                        )
                        is_valid_default_name = (
                            check_valid_value(feature, name_field['field'])
                        )
                        if not is_valid_default_name:
                            error_found = True
                            layer_error[ErrorType.NAME_FIELDS_ERROR.value] = (
                                ERROR_CHECK
                            )
                            level_error_report[
                                ErrorType.NAME_FIELDS_ERROR.value] += 1
                            # no need to proceed the other name
                            break
                    if name_field_value:
                        name_fields.append({
                            'language': (
                                name_field['selectedLanguage'] if
                                'selectedLanguage' in name_field and
                                name_field['selectedLanguage'] else None
                            ),
                            'name': name_field['field'],
                            'default': name_field['default'],
                            'value': name_field_value,
                            'label': (
                                name_field['label'] if
                                'label' in name_field and
                                name_field['label'] else None
                            ),
                            'name_field_idx': name_field_idx
                        })

                # Check id fields
                id_fields = []
                for id_field in layer_file.id_fields:
                    id_field_value = (
                        get_feature_value(feature, id_field['field'])
                    )
                    if id_field['default']:
                        # if default code, then validate the value
                        internal_code = id_field_value
                        layer_error[ENTITY_CODE] = internal_code
                        is_valid_default_code = (
                            check_valid_value(feature, id_field['field'])
                        )
                        if not is_valid_default_code:
                            error_found = True
                            layer_error[ErrorType.ID_FIELDS_ERROR.value] = (
                                ERROR_CHECK
                            )
                            level_error_report[
                                ErrorType.ID_FIELDS_ERROR.value] += 1
                            # no need to proceed the other id
                            break
                    if id_field_value:
                        id_fields.append({
                            'id_type': id_field['idType']['id'],
                            'field': id_field['field'],
                            'default': id_field['default'],
                            'value': id_field_value
                        })

                # Check hierarchy via parent codes
                if parent_entities:
                    feature_rematched_parent = children_lv1.filter(
                        feature_index=feature_idx
                    ).exists()
                    if (level == 1 and feature_rematched_parent):
                        # we skip validation if
                        # it is level 1+has parent matching
                        pass
                    elif feature_parent_code not in parent_entities_codes:
                        error_found = True
                        layer_error[ErrorType.PARENT_CODE_HIERARCHY.value] = (
                            ERROR_CHECK
                        )
                        level_error_report[
                            ErrorType.PARENT_CODE_HIERARCHY.value] += 1

                # Check duplicate default code if valid default code
                if not layer_error[ErrorType.ID_FIELDS_ERROR.value]:
                    default_code_dupes = GeographicalEntity.objects.filter(
                        layer_file=layer_file,
                        internal_code=internal_code
                    ).exists()
                    layer_error[ErrorType.DUPLICATED_CODES.value] = (
                        ERROR_CHECK if default_code_dupes else ''
                    )
                    if layer_error[ErrorType.DUPLICATED_CODES.value]:
                        error_found = True
                        level_error_report[
                            ErrorType.DUPLICATED_CODES.value
                        ] += 1

                # check privacy level in feature layer file
                geo_privacy_level = dataset.max_privacy_level
                is_valid_privacy_level = True
                if layer_file.privacy_level:
                    geo_privacy_level = int(layer_file.privacy_level)
                elif layer_file.privacy_level_field:
                    # check for valid value of privacy level
                    is_valid_privacy_level = (
                        check_valid_value(feature,
                                          layer_file.privacy_level_field)
                    )
                    if is_valid_privacy_level:
                        privacy_level_value = (
                            get_feature_value(feature,
                                              layer_file.privacy_level_field)
                        )
                        try:
                            geo_privacy_level = int(privacy_level_value)
                        except ValueError:
                            is_valid_privacy_level = False
                    layer_error[ErrorType.PRIVACY_LEVEL_ERROR.value] = (
                        ERROR_CHECK if not is_valid_privacy_level else ''
                    )
                    if layer_error[ErrorType.PRIVACY_LEVEL_ERROR.value]:
                        error_found = True
                        level_error_report[
                            ErrorType.PRIVACY_LEVEL_ERROR.value
                        ] += 1

                # validate max privacy level in dataset
                is_allowed_privacy_level = True
                if not is_valid_privacy_level:
                    is_allowed_privacy_level = False
                else:
                    is_allowed_privacy_level = (
                        geo_privacy_level <= dataset.max_privacy_level
                    )
                layer_error[ErrorType.INVALID_PRIVACY_LEVEL.value] = (
                    ERROR_CHECK if not is_allowed_privacy_level else ''
                )
                if layer_error[ErrorType.INVALID_PRIVACY_LEVEL.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.INVALID_PRIVACY_LEVEL.value
                    ] += 1

                if is_valid_privacy_level and is_allowed_privacy_level:
                    # check against min privacy level in dataset
                    if geo_privacy_level < dataset.min_privacy_level:
                        # upgrade to min_privacy_level
                        geo_privacy_level = dataset.min_privacy_level
                        # flat to ui using allowable error type
                        error_found = True
                        layer_error[ErrorType.UPGRADED_PRIVACY_LEVEL.value] = (
                            ERROR_CHECK
                        )
                        level_error_report[
                            ErrorType.UPGRADED_PRIVACY_LEVEL.value
                        ] += 1

                geom_str = json.dumps(feature['geometry'])
                geom = do_valid_nodes_check(geom_str, internal_code,
                                            entity_upload, **kwargs)
                if geom is None:
                    # invalid geom
                    error_found = True
                    layer_error[ErrorType.DEGENERATE_POLYGON.value] = (
                        ERROR_CHECK
                    )
                    validation_summaries.append(layer_error)
                    level_error_report[
                        ErrorType.DEGENERATE_POLYGON.value
                    ] += 1
                    continue
                elif isinstance(geom, Polygon):
                    geom = MultiPolygon([geom])

                # GEOMETRY VALIDITY CHECKS
                # Check self intersects
                is_valid_self_intersects = do_self_intersects_check(
                    geom, internal_code, entity_upload, **kwargs
                )
                layer_error[ErrorType.SELF_INTERSECTS.value] = (
                    ERROR_CHECK if not is_valid_self_intersects else ''
                )
                if layer_error[ErrorType.SELF_INTERSECTS.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.SELF_INTERSECTS.value
                    ] += 1

                # Check self contacts
                # skipping self contacts check until has better performance
                # is_valid_self_contacts = do_self_contact_check(
                #     geom, internal_code, entity_upload
                # )
                # layer_error[ErrorType.SELF_CONTACTS.value] = (
                #     ERROR_CHECK if not is_valid_self_contacts else ''
                # )
                # if layer_error[ErrorType.SELF_CONTACTS.value]:
                #     error_found = True
                #     level_error_report[
                #         ErrorType.SELF_CONTACTS.value
                #     ] += 1

                # Check duplicate nodes
                is_valid_duplicate_nodes = do_duplicate_nodes_check(
                    geom, internal_code, entity_upload, **kwargs
                )
                layer_error[ErrorType.DUPLICATE_NODES.value] = (
                    ERROR_CHECK if not is_valid_duplicate_nodes else ''
                )
                if layer_error[ErrorType.DUPLICATE_NODES.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.DUPLICATE_NODES.value
                    ] += 1

                # GEOMETRY TOPOLOGY CHECKS
                # Check duplicate geometry
                is_valid_duplicate_geom = do_duplicate_check(
                    geom, internal_code, entity_upload, layer_file, **kwargs
                )
                layer_error[ErrorType.DUPLICATE_GEOMETRIES.value] = (
                    ERROR_CHECK if not is_valid_duplicate_geom else ''
                )
                if layer_error[ErrorType.DUPLICATE_GEOMETRIES.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.DUPLICATE_GEOMETRIES.value
                    ] += 1

                # Check overlaps
                is_valid_overlaps = do_overlap_check(
                    geom, internal_code, entity_upload, layer_file, **kwargs
                )
                layer_error[ErrorType.OVERLAPS.value] = (
                    ERROR_CHECK if not is_valid_overlaps else ''
                )
                if layer_error[ErrorType.OVERLAPS.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.OVERLAPS.value
                    ] += 1

                # Check hierarchy by geometry
                is_valid_hierarchy = do_hierarchy_check(
                    geom, internal_code, entity_upload, parent, **kwargs
                )
                layer_error[ErrorType.GEOMETRY_HIERARCHY.value] = (
                    ERROR_CHECK if not is_valid_hierarchy else ''
                )
                if layer_error[ErrorType.GEOMETRY_HIERARCHY.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.GEOMETRY_HIERARCHY.value
                    ] += 1

                # Get uuid concept, create random at layer validation
                # at boundary matching, it will be matched with previous rev
                uuid_str = str(uuid.uuid4())

                geo_entity_type_label = None
                if layer_file.entity_type:
                    geo_entity_type_label = layer_file.entity_type
                elif layer_file.location_type_field:
                    geo_entity_type_label = feature_properties[
                        layer_file.location_type_field]
                geo_entity_type = EntityType.objects.get_by_label(
                    geo_entity_type_label
                )

                if error_found:
                    validation_summaries.append(layer_error)
                # only create the entity if parent exists for level > 0
                if level >= 1 and not parent:
                    continue
                start_date = (
                    entity_upload.upload_session.started_at if
                    not entity_upload.upload_session.is_historical_upload else
                    entity_upload.upload_session.historical_start_date
                )
                end_date = (
                    entity_upload.upload_session.historical_end_date if
                    entity_upload.upload_session.is_historical_upload else
                    None
                )
                geo, updated = GeographicalEntity.objects.update_or_create(
                    parent=parent,
                    uuid=uuid_str,
                    revision_number=revision,
                    level=level,
                    defaults={
                        'layer_file': layer_file,
                        'dataset': (
                            entity_upload.upload_session.dataset
                        ),
                        'start_date': start_date,
                        'end_date': end_date,
                        'type': geo_entity_type,
                        'label': label,
                        'internal_code': str(internal_code),
                        'geometry': geom,
                        'is_approved': None,
                        'is_validated': False,
                        'is_latest': False,
                        'ancestor': ancestor if level != 0 else None,
                        'admin_level_name': admin_level_name,
                        'privacy_level': geo_privacy_level,
                        'bbox': (
                            '[' + ','.join(map(str, geom.extent)) +
                            ']'
                        ),
                        'centroid': geom.point_on_surface.wkt
                    }
                )
                feature_included_idx += 1
                for name_field in name_fields:
                    try:
                        EntityName.objects.create(
                            language_id=name_field['language'],
                            name=name_field['value'],
                            geographical_entity=geo,
                            default=name_field['default'],
                            label=name_field['label'],
                            idx=name_field['name_field_idx']
                        )
                    except IntegrityError:
                        pass

                for id_field in id_fields:
                    try:
                        EntityId.objects.create(
                            code_id=id_field['id_type'],
                            value=id_field['value'],
                            default=id_field['default'],
                            geographical_entity=geo
                        )
                    except IntegrityError:
                        pass

                if (
                    level == 0 and
                        not entity_upload.revised_geographical_entity
                ):
                    entity_upload.revised_geographical_entity = geo
                    entity_upload.revision_number = revision
                    entity_upload.save()
                    ancestor = entity_upload.revised_geographical_entity
                    # for level 0, only needs to read 1 feature
                    break
            # for contained_check + gap_check at level 0,
            # we cannot do at this run_validation since
            # this processes only 1 adm 0 entity
            if level > 0:
                feature_included_idx = 0
                entities = GeographicalEntity.objects.filter(
                    dataset=dataset,
                    layer_file=layer_file,
                    level=level,
                    ancestor=entity_upload.revised_geographical_entity
                )
                # we can do contained check if all features have been inserted
                for entity in entities:
                    is_valid = do_contained_check(
                        entity,
                        entity_upload,
                        layer_file,
                        **kwargs
                    )
                    entity_upload.progress = (
                        f'Level {level} - Contained Check '
                        f'({feature_included_idx + 1} of '
                        f'{total_features} polygons)'
                    )
                    entity_upload.save(update_fields=['progress'])
                    feature_included_idx += 1
                    if is_valid:
                        continue
                    # find layer_error from validation_summaries
                    layer_errors = [x for x in validation_summaries if
                                    x[ENTITY_CODE] == entity.internal_code]
                    if layer_errors:
                        layer_error = layer_errors[0]
                    else:
                        # create new layer_error and
                        # add to validation_summaries
                        layer_error = create_layer_error(
                            level, entity.internal_code, entity.label)
                    layer_error[
                        ErrorType.WITHIN_OTHER_FEATURES.value] = ERROR_CHECK
                    if len(layer_errors) == 0:
                        validation_summaries.append(layer_error)
                    # set flag to level_error_report
                    level_error_report[
                        ErrorType.WITHIN_OTHER_FEATURES.value] += 1
                entity_upload.progress = (
                    f'Level {level} - Gaps Check ({total_features} polygons)'
                )
                entity_upload.save(update_fields=['progress'])
                # run gaps check for entities at current parent
                is_valid, errors = do_gap_check(entity_upload,
                                                layer_file,
                                                level,
                                                **kwargs)
                if not is_valid:
                    # set flag to level_error_report
                    level_error_report[ErrorType.GAPS.value] = len(errors)
            logger.debug(level_error_report)
            error_summaries.append(level_error_report)
            delete_tmp_shapefile(layer.path)

    if (
        entity_upload.revised_entity_id and
            not entity_upload.revised_geographical_entity
    ):
        # entity level 0 is not found in the layer files
        layer_error = {
            LEVEL: 0,
        }
        for error_type in ErrorType:
            layer_error[error_type.value] = ''
        layer_error[ErrorType.ID_FIELDS_ERROR.value] = ERROR_CHECK
        validation_summaries.append(layer_error)
        level0_idx_error = next(
                (index for (index, d) in enumerate(error_summaries) if
                    d[LEVEL] == 0),
                None
        )
        if level0_idx_error is not None:
            error_summaries[
                level0_idx_error
            ][ErrorType.ID_FIELDS_ERROR.value] += 1

    if len(validation_summaries) > 0:
        # check whether the errors are blocking/non-blocking
        (
            allowable_errors, blocking_errors, _, _
        ) = count_error_categories(error_summaries)
        if allowable_errors > 0 and blocking_errors == 0:
            entity_upload.status = WARNING
        else:
            entity_upload.status = ERROR
        entity_upload.summaries = error_summaries
        # Save error report to csv
        try:
            keys = validation_summaries[0].keys()
            csv_buffer = StringIO()
            csv_writer = csv.DictWriter(csv_buffer, keys)
            csv_writer.writeheader()
            csv_writer.writerows(validation_summaries)

            csv_file = ContentFile(csv_buffer.getvalue().encode('utf-8'))
            entity_upload.error_report.save(
                f'error-report-{entity_upload.id}.csv',
                csv_file
            )
        except Exception as e:
            logger.error(e)
    else:
        entity_upload.status = VALID

    entity_upload.save()
    # do simplification for dataset if only 1 upload in session
    upload_count = EntityUploadStatus.objects.filter(
        upload_session=entity_upload.upload_session
    ).count()
    if upload_count == 1:
        simplify_for_dataset(dataset)
    # note: error/invalid geometries will be removed
    # if it's not selected to be imported
    logger.info(f'finished validation admin_boundaries {entity_upload.id}')

    end = time.time()
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.run_validation',
            end - start)

    return entity_upload.status == VALID


def count_error_categories(error_summaries):
    """
    Return Tuple of:
        - allowable_errors
        - blocking_errors
        - superadmin_bypass_errors
        - superadmin_blocking_errors
    """
    allowable_errors = 0
    blocking_errors = 0
    superadmin_bypass_errors = 0
    superadmin_blocking_errors = 0
    for error_summary in error_summaries:
        for error_type in ErrorType:
            if error_type.value not in error_summary:
                continue
            if error_type in ALLOWABLE_ERROR_TYPES:
                allowable_errors += error_summary[error_type.value]
            else:
                blocking_errors += error_summary[error_type.value]
            if error_type in SUPERADMIN_BYPASS_ERROR:
                superadmin_bypass_errors += (
                    error_summary[error_type.value]
                )
            else:
                superadmin_blocking_errors += (
                    error_summary[error_type.value]
                )
    return (allowable_errors, blocking_errors, superadmin_bypass_errors,
            superadmin_blocking_errors)


def is_validation_result_importable(
        entity_upload: EntityUploadStatus,
        user,
        **kwargs) -> Tuple[bool, bool]:
    """
    Return:
     is_importable: whether the validation result can still be imported
     is_warning: whether the errors are considered as non-blocking error
    """
    start = time.time()

    is_warning = entity_upload.status == WARNING
    is_importable = entity_upload.status in IMPORTABLE_UPLOAD_STATUS_LIST
    if not is_importable and entity_upload.summaries:
        # check whether the errors are blocking/non-blocking
        (
            allowable_errors, blocking_errors, superadmin_bypass_errors,
            superadmin_blocking_errors
        ) = count_error_categories(entity_upload.summaries)
        if allowable_errors > 0 and blocking_errors == 0:
            is_importable = True
        # check if superadmin user:
        if user and user.is_superuser:
            if (
                superadmin_bypass_errors > 0 and
                superadmin_blocking_errors == 0
            ):
                is_importable = True

    end = time.time()
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.is_validation_result_importable',
            end - start)
    return is_importable, is_warning


def reset_qc_validation(upload_session: LayerUploadSession, **kwargs):
    """
    Reset entity uploads in upload_session
    """
    start = time.time()

    uploads = EntityUploadStatus.objects.filter(
        upload_session=upload_session
    )
    for upload in uploads:
        if upload.task_id:
            app.control.revoke(
                upload.task_id,
                terminate=True,
                signal='SIGKILL'
            )
        # delete revised entity level 0
        if upload.revised_geographical_entity:
            upload.revised_geographical_entity.delete()
        upload.status = ''
        upload.logs = ''
        upload.summaries = None
        upload.error_report = None
        upload.task_id = ''
        upload.revised_geographical_entity = None
        upload.save()

    upload_session.current_process = None
    upload_session.current_process_uuid = None
    upload_session.save(update_fields=['current_process',
                                       'current_process_uuid'])
    end = time.time()
    if kwargs.get('log_object'):
        kwargs['log_object'].add_log(
            'admin_boundaries.qc_validation.reset_qc_validation',
            end - start)


def get_error_types():
    error_types = []
    nonblocking_types = []
    for error_type in ErrorType:
        if error_type in ALLOWABLE_ERROR_TYPES:
            nonblocking_types.append(error_type.value)
        else:
            error_types.append(error_type.value)
    return {
        'error': error_types,
        'warning': nonblocking_types
    }
