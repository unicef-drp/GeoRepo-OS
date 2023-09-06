from dashboard.models import LayerFile


def is_valid(layer_file: LayerFile):
    return (
        layer_file.boundary_type != '' and
        (layer_file.privacy_level_field != '' or
            layer_file.privacy_level != '')
    )


def get_summary(layer_file: LayerFile):
    privacy_level_field = f'privacy_level_field = '\
        f'{layer_file.privacy_level_field}'
    if layer_file.privacy_level != '':
        privacy_level_field = f'privacy_level = '\
            f'\'{layer_file.privacy_level}\''
    summary_data = {
        'id': layer_file.id,
        'level': layer_file.level,
        'file_name': (
            layer_file.layer_file.name.split('/')
        )[-1],
        'field_mapping': [
            f'{privacy_level_field}',
            f'boundary_type = {layer_file.boundary_type}'
        ]
    }

    for id_field in layer_file.id_fields:
        id_field_value = id_field["field"]
        summary_data['field_mapping'].append(
            f'id_field ({id_field["idType"]["name"]}) = '
            f'{id_field_value}'
        )
    summary_data['feature_count'] = layer_file.feature_count
    summary_data['valid'] = True
    return summary_data
