from celery import shared_task
import logging

from django.db import IntegrityError
from georepo.utils.module_import import module_function
from dashboard.models import (
    LayerUploadSession, DONE,
    LayerFile, SHAPEFILE
)

logger = logging.getLogger(__name__)


@shared_task(name='fix_entity_name_encoding')
def fix_entity_name_encoding(dataset_id):
    import fiona
    from georepo.models import Dataset, GeographicalEntity, EntityName
    from georepo.utils.layers import get_feature_value
    logger.info(f'Running fix_entity_name_encoding of dataset {dataset_id}')
    dataset = Dataset.objects.get(id=dataset_id)
    upload_sessions = LayerUploadSession.objects.filter(
        dataset=dataset,
        status=DONE
    )
    for upload_session in upload_sessions:
        layer_files = LayerFile.objects.filter(
            layer_upload_session=upload_session
        )
        logger.info(f'Fetching layer_files from session {upload_session.id} '
                    f'with count {layer_files.count()} ')
        for layer_file in layer_files:
            layer_file_path = layer_file.layer_file.path
            if layer_file.layer_type == SHAPEFILE:
                layer_file_path = f'zip://{layer_file.layer_file.path}'
            with fiona.open(layer_file_path, encoding='utf-8') as layer:
                total_features = len(layer)
                logger.info(f'Patching {total_features} entities '
                            f'from level {layer_file.level} '
                            f'of layer_file {layer_file.id}')
                for feature_idx, feature in enumerate(layer):
                    internal_code = None
                    # find internal_code
                    for id_field in layer_file.id_fields:
                        if id_field['default']:
                            internal_code = get_feature_value(
                                feature,
                                id_field['field']
                            )
                            break
                    if internal_code is None:
                        continue
                    entity = GeographicalEntity.objects.filter(
                        dataset=dataset,
                        layer_file=layer_file,
                        internal_code=internal_code
                    ).first()
                    if not entity:
                        continue
                    name_fields = []
                    for name_field_idx, name_field in enumerate(
                        layer_file.name_fields
                    ):
                        name_field_value = (
                            get_feature_value(feature, name_field['field'])
                        )
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
                    if name_fields:
                        # remove old names
                        EntityName.objects.filter(
                            geographical_entity=entity
                        ).delete()
                        for name_field in name_fields:
                            if name_field['default']:
                                # update default label
                                entity.label = name_field_value
                                entity.save(update_fields=['label'])
                            try:
                                EntityName.objects.create(
                                    language_id=name_field['language'],
                                    name=name_field['value'],
                                    geographical_entity=entity,
                                    default=name_field['default'],
                                    label=name_field['label'],
                                    idx=name_field['name_field_idx']
                                )
                            except IntegrityError:
                                pass
                    if feature_idx % 10 == 0:
                        logger.info(f'Patching {feature_idx+1}/'
                                    f'{total_features}')
                logger.info(f'Finished patching {feature_idx+1}/'
                            f'{total_features}')


@shared_task(name='do_generate_adm0_default_views')
def do_generate_adm0_default_views(dataset_id):
    from georepo.models import Dataset
    dataset = Dataset.objects.get(id=dataset_id)
    logger.info('Running do_generate_adm0_default_views of '
                f'dataset {dataset_id} - {str(dataset)}')
    generate_adm0 = module_function(
        dataset.module.code_name,
        'config',
        'generate_adm0_default_views'
    )
    generate_adm0(dataset)
    logger.info('Finished do_generate_adm0_default_views of '
                f'dataset {dataset_id} - {str(dataset)}')
