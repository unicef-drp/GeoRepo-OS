import os
import json
import fiona
from typing import Tuple

from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon

from georepo.models import (
    GeographicalEntity,
    EntityType,
    CodeCL,
    EntityCode,
    Dataset,
)


def load_layer_feature(
        feature: any,
        index: int,
        total_features: int,
        upload_session: any,
        level: int,
        entity_type: EntityType,
        name_field: str,
        dataset: str = None,
        code_field: str = None) -> Tuple[bool, str, bool]:
    # load single feature into GeographicalEntity object
    # return (Success, ErrorMessage, Created)
    geom_str = json.dumps(feature['geometry'])
    properties = feature['properties']
    geom = GEOSGeometry(geom_str)
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    if not isinstance(geom, MultiPolygon):
        raise TypeError(
            'Type is not acceptable'
        )
    label = name_field.format(level=level)
    code = code_field.format(level=level)

    if label not in properties or code not in properties:
        return (False, 'Label or code format not found in the layer', False)

    entity, created = GeographicalEntity.objects.update_or_create(
        label=properties[label],
        type=entity_type,
        internal_code=properties[code],
        defaults={
            'geometry': geom,
            'dataset': dataset,
            'level': level,
            'is_approved': True,
            'is_latest': True,
        }
    )

    if upload_session:
        upload_session.progress = f'Processing ({index}/{total_features})'
        upload_session.save()

    entity.level = level
    entity.save()

    code_cl, _ = CodeCL.objects.get_or_create(
        name='admin'
    )
    EntityCode.objects.get_or_create(
        code_cl=code_cl,
        entity=entity,
        code=properties[code]
    )

    if level > 0:
        try:
            parent_code_field = code_field.format(
                level=level - 1
            )
            parent = GeographicalEntity.objects.get(
                internal_code__iexact=properties[parent_code_field],
                level=level - 1
            )
            entity.parent = parent
            entity.save()
        except (KeyError, GeographicalEntity.DoesNotExist):
            pass
    return (True, '', created)


def load_layer_file(
        layer_type: str,
        file_path: str,
        level: int,
        entity_type: EntityType,
        name_field: str,
        dataset: str = None,
        code_field: str = None,
        layer_upload_session_id: str = None) -> Tuple[bool, str]:
    if not os.path.exists(file_path):
        return (False, 'File does not exist')

    entity_added = 0
    entity_updated = 0
    total_features = 0

    upload_session = None
    if layer_upload_session_id:
        from dashboard.models import LayerUploadSession
        upload_session = LayerUploadSession.objects.get(
            id=layer_upload_session_id
        )

    if dataset:
        dataset, _ = Dataset.objects.get_or_create(
            label=dataset
        )

    if layer_type == 'GEOJSON':
        with open(file_path) as json_file:
            data = json.load(json_file)
            features = data['features']
            total_features = len(features)
            index = 1
            for feature in features:
                success, error, created = load_layer_feature(
                            feature, index, total_features,
                            upload_session, level, entity_type,
                            name_field, dataset, code_field
                        )
                if not success:
                    return (False, error)
                if created:
                    entity_added += 1
                else:
                    entity_updated += 1
                index += 1
    elif layer_type == 'SHAPEFILE':
        layers = fiona.listlayers(f'zip://{file_path}')
        if not layers:
            return (False, 'Zip shape file has no layer')
        # we can read only 1 layer inside the zip file
        with fiona.open(f'zip://{file_path}',
                        encoding='utf-8', layer=0) as features:
            total_features = len(features)
            index = 1
            for feature in features:
                success, error, created = load_layer_feature(
                            feature, index, total_features,
                            upload_session, level, entity_type,
                            name_field, dataset, code_field
                        )
                if not success:
                    return (False, error)
                if created:
                    entity_added += 1
                else:
                    entity_updated += 1
                index += 1
    elif layer_type == 'GEOPACKAGE':
        layers = fiona.listlayers(file_path)
        if not layers:
            return (False, 'Geopackage file has no layer')
        # we can read only 1 layer inside the geopackage file
        with fiona.open(file_path, encoding='utf-8', layer=0) as features:
            total_features = len(features)
            index = 1
            for feature in features:
                success, error, created = load_layer_feature(
                            feature, index, total_features,
                            upload_session, level, entity_type,
                            name_field, dataset, code_field
                        )
                if not success:
                    return (False, error)
                if created:
                    entity_added += 1
                else:
                    entity_updated += 1
                index += 1
    else:
        raise NotImplementedError(
            f'Load layer type {layer_type} is not implemented!')

    if upload_session:
        desc = (
            f'-- {entity_type.label} Entity Type --\n'
            f'{entity_added} {"entity" if entity_added == 1 else "entities"} '
            f'is added\n'
            f'{entity_updated} '
            f'{"entity" if entity_updated == 1 else "entities"} is updated\n\n'
        )
        if not upload_session.message:
            upload_session.message = desc
        else:
            upload_session.message += desc
        upload_session.save()

    return (True, '')
