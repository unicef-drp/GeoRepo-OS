import collections.abc
from georepo.models import Language
from dashboard.models import LayerFile, PrivacyLevel


def is_valid(layer_file: LayerFile):
    name_field_found = False
    id_field_found = False
    if layer_file.name_fields and isinstance(
            layer_file.name_fields, collections.abc.Sequence):
        for name_field in layer_file.name_fields:
            if name_field['field'] and name_field['default']:
                name_field_found = True
                break

    if layer_file.id_fields and isinstance(
            layer_file.id_fields, collections.abc.Sequence):
        for id_field in layer_file.id_fields:
            if id_field['field'] and id_field['default']:
                id_field_found = True
                break

    if layer_file.level == '0':
        parent_id_field_valid = True
    else:
        parent_id_field_valid = layer_file.parent_id_field != ''

    return (
        (layer_file.location_type_field != '' or
            layer_file.entity_type != '') and
        (layer_file.privacy_level_field != '' or
            layer_file.privacy_level != '') and
        parent_id_field_valid and
        name_field_found and
        id_field_found
    )


def get_summary(layer_file: LayerFile):
    privacy_level_field = f'privacy_level_field = '\
        f'{layer_file.privacy_level_field}'
    if layer_file.privacy_level != '':
        privacy_level_label = PrivacyLevel.objects.filter(
            privacy_level=int(layer_file.privacy_level)
        ).first()
        if privacy_level_label:
            privacy_level_field = f'privacy_level = '\
                f'\'{layer_file.privacy_level} - '\
                f'{privacy_level_label.label}\''
        else:
            privacy_level_field = f'privacy_level = '\
                f'\'{layer_file.privacy_level}\''
    location_type_field = f'location_type_field = '\
        f'{layer_file.location_type_field}'
    if layer_file.entity_type != '':
        location_type_field = f'location_type = '\
            f'\'{layer_file.entity_type}\''
    summary_data = {
        'id': layer_file.id,
        'level': layer_file.level,
        'file_name': (
            layer_file.layer_file.name.split('/')
        )[-1],
        'field_mapping': []
    }
    for name_field in layer_file.name_fields:
        _language = ''
        if (
            'selectedLanguage' in name_field and
            name_field['selectedLanguage']
        ):
            language = Language.objects.get(
                id=name_field["selectedLanguage"])
            _language = f' ({language.name})'
        name_field_value = name_field["field"]
        if name_field["default"]:
            name_field_value += " (default)"
        name_field_label = (
            ' - {label}'.format(label=name_field['label']) if
            'label' in name_field and
            name_field['label'] else ''
        )
        summary_data['field_mapping'].append(
            f'name_field{name_field_label}{_language} = '
            f'{name_field_value}'
        )

    for id_field in layer_file.id_fields:
        id_field_value = id_field["field"]
        if id_field["default"]:
            id_field_value += " (default)"
        summary_data['field_mapping'].append(
            f'id_field ({id_field["idType"]["name"]}) = '
            f'{id_field_value}'
        )
    summary_data['field_mapping'].extend([
        f'parent_id_field = {layer_file.parent_id_field}',
        f'{location_type_field}',
        f'{privacy_level_field}',
        f'source_id_field = {layer_file.source_field}'
    ])
    summary_data['feature_count'] = layer_file.feature_count
    summary_data['valid'] = True
    return summary_data
