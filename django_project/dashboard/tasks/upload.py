from celery import shared_task
import logging
import time
import uuid
import traceback
from core.celery import app
from django.utils import timezone
from django.contrib.auth import get_user_model
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity
from dashboard.models import (
    LayerUploadSession, EntityUploadStatusLog,
    STARTED,
    EntityUploadStatus,
    REVIEWING,
    LayerUploadSessionActionLog,
    LayerFile
)
from georepo.tasks import validate_ready_uploads
from georepo.utils.module_import import module_function
from georepo.utils.celery_helper import cancel_task

UserModel = get_user_model()
logger = logging.getLogger(__name__)


def create_log_object_for_session(upload_session):
    result = None
    try:
        result, _ = EntityUploadStatusLog.objects.get_or_create(
            layer_upload_session=upload_session,
            entity_upload_status__isnull=True
        )
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
    return result


def create_log_object_for_upload(upload, parent_log):
    result = None
    if parent_log is None:
        return result
    try:
        result, _ = EntityUploadStatusLog.objects.get_or_create(
            entity_upload_status=upload,
            parent_log=parent_log
        )
    except Exception as ex:
        logger.error(ex)
        logger.error(traceback.format_exc())
    return result


def validate_selected_country(upload_session, entities, **kwargs):
    start = time.time()
    country_ids = [
        entity_upload['country_entity_id'] for
        entity_upload in entities if entity_upload['country_entity_id']
    ]
    other_uploads = EntityUploadStatus.objects.filter(
        original_geographical_entity__id__in=country_ids,
        upload_session__dataset=upload_session.dataset,
        status=REVIEWING
    ).exclude(
        upload_session=upload_session
    )
    if other_uploads.exists():
        uploads = other_uploads[:3]
        other_countries = []
        for upload in uploads:
            if upload.original_geographical_entity:
                other_countries.append(
                    upload.original_geographical_entity.internal_code
                )
            elif upload.revised_entity_id:
                other_countries.append(
                    upload.revised_entity_id
                )
        return (
            False,
            f'There are {other_uploads.count()} countries '
            'has upload being reviewed: ' +
            ', '.join(other_countries)
        )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'ValidateUploadSession.validate_selected_country',
            end - start)
    return True, ''


def validate_selected_country_for_review(dataset: Dataset, user, uploads):
    is_importable_func = module_function(
        dataset.module.code_name,
        'qc_validation',
        'is_validation_result_importable'
    )
    for entity_upload in uploads:
        upload_session = entity_upload.upload_session
        if entity_upload.original_geographical_entity:
            country = entity_upload.original_geographical_entity.label
            other_uploads = EntityUploadStatus.objects.filter(
                original_geographical_entity=(
                    entity_upload.original_geographical_entity
                ),
                upload_session__dataset=upload_session.dataset,
                status=REVIEWING
            ).exclude(
                upload_session=upload_session
            )
            if other_uploads.exists():
                return False, f'{country} has upload being reviewed'
        else:
            country = entity_upload.revised_entity_name
        is_importable, _ = is_importable_func(
            entity_upload,
            user
        )
        if not is_importable:
            return False, (
                f'{country} cannot be imported because '
                'there is validation error!'
            )
    return True, ''


def get_entities_data(entities):
    results = []
    for entity in entities:
        is_default = False
        if 'default' in entity:
            is_default = entity['default']
        if is_default and 'upload_id' not in entity:
            continue
        if is_default:
            upload_id = entity['upload_id']
            upload = EntityUploadStatus.objects.filter(
                id=upload_id
            ).first()
            if not upload:
                continue
            ori_entity = upload.original_geographical_entity
            layer0_id = (
                ori_entity.internal_code if ori_entity
                else upload.revised_entity_id
            )
            country = (
                ori_entity.label if ori_entity else upload.revised_entity_name
            )
            results.append({
                'id': str(ori_entity.id) if ori_entity else str(uuid.uuid4()),
                'country': country,
                'layer0_id': layer0_id,
                'country_entity_id': ori_entity.id if ori_entity else None,
                'max_level': upload.max_level_in_layer,
                'upload_id': upload_id,
                'admin_level_names': upload.admin_level_names,
                'default': True
            })
        else:
            results.append(entity)
    return results


@shared_task(name="process_country_selection")
def process_country_selection(session_action_id):
    """Run process country selection."""
    logger.info(f'Running process_country_selection {session_action_id}')
    action_data = LayerUploadSessionActionLog.objects.get(
        id=session_action_id)
    action_data.on_started()
    start = time.time()
    upload_session = action_data.session
    entities = get_entities_data(action_data.data['entities'])
    upload_log = create_log_object_for_session(upload_session)
    is_selected_valid, error = validate_selected_country(
        upload_session,
        entities,
        **{'log_object': upload_log}
    )
    if not is_selected_valid:
        end = time.time()
        if upload_log:
            upload_log.add_log('process_country_selection', end - start)
        action_data.on_finished(True, {
            'is_valid': False,
            'error': error
        })
        return
    entity_upload_ids = []
    for entity_upload in entities:
        max_level = int(entity_upload['max_level'])
        layer0_id = entity_upload['layer0_id']
        country = entity_upload['country']
        if entity_upload['country_entity_id']:
            entity_upload_status, _ = (
                EntityUploadStatus.objects.update_or_create(
                    original_geographical_entity_id=(
                        entity_upload['country_entity_id']
                    ),
                    upload_session=upload_session,
                    defaults={
                        'status': STARTED,
                        'logs': '',
                        'max_level': max_level,
                        'started_at': timezone.now(),
                        'summaries': None,
                        'error_report': None,
                        'admin_level_names': (
                            entity_upload['admin_level_names']
                        )
                    }
                )
            )
            entity_upload_ids.append(entity_upload_status.id)
        else:
            entity_upload_status, _ = (
                EntityUploadStatus.objects.update_or_create(
                    revised_entity_id=layer0_id,
                    revised_entity_name=country,
                    upload_session=upload_session,
                    defaults={
                        'status': STARTED,
                        'logs': '',
                        'max_level': max_level,
                        'started_at': timezone.now(),
                        'summaries': None,
                        'error_report': None,
                        'admin_level_names': (
                            entity_upload['admin_level_names']
                        )
                    }
                )
            )
            entity_upload_ids.append(entity_upload_status.id)
        if entity_upload_status.task_id:
            app.control.revoke(
                entity_upload_status.task_id,
                terminate=True,
                signal='SIGKILL'
            )
        upload_log_entity = create_log_object_for_upload(
            entity_upload_status, upload_log)
        # trigger validation task
        task = validate_ready_uploads.apply_async(
            (
                entity_upload_status.id,
                upload_log_entity.id if upload_log_entity else None
            ),
            queue='validation'
        )
        entity_upload_status.task_id = task.id
        entity_upload_status.save(update_fields=['task_id'])
    # delete/reset the other entity uploads
    other_uploads = EntityUploadStatus.objects.filter(
        upload_session=upload_session
    ).exclude(id__in=entity_upload_ids)
    for upload in other_uploads:
        upload.status = ''
        upload.logs = ''
        upload.max_level = ''
        upload.summaries = None
        revised = None
        if upload.revised_geographical_entity:
            revised = upload.revised_geographical_entity
            upload.revised_geographical_entity = None
        if upload.error_report:
            upload.error_report.delete(save=False)
            upload.error_report = None
        if upload.task_id:
            app.control.revoke(
                upload.task_id,
                terminate=True,
                signal='SIGKILL'
            )
            upload.task_id = ''
        upload.save()
        # this will removed entities from non-selected upload
        if revised:
            revised.delete()

    end = time.time()
    if upload_log:
        upload_log.add_log('process_country_selection', end - start)
    action_data.on_finished(True, {
        'is_valid': True,
        'error': None
    })
    # update session step
    upload_session.last_step = 4
    upload_session.save(update_fields=['last_step'])


@shared_task(name="process_country_selection_for_review")
def process_country_selection_for_review(session_action_id, user_id):
    """Run process country selection for review."""
    logger.info(f'Running process_country_selection_for_review '
                f'{session_action_id}')
    action_data = LayerUploadSessionActionLog.objects.get(
        id=session_action_id)
    action_data.on_started()
    user = UserModel.objects.get(id=user_id)
    start = time.time()
    upload_session = action_data.session
    upload_entities = action_data.data['upload_entities']
    upload_log = create_log_object_for_session(upload_session)
    upload_entity_ids = upload_entities.split(',')
    uploads = EntityUploadStatus.objects.filter(
        id__in=upload_entity_ids
    )
    upload_session = LayerUploadSession.objects.filter(
        id__in=uploads.values('upload_session')
    )
    upload_session_obj: LayerUploadSession = upload_session.first()
    dataset: Dataset = upload_session_obj.dataset
    # validate the imported countries has not in-review in other session
    is_selected_valid, error = validate_selected_country_for_review(
        dataset, user, uploads)
    if not is_selected_valid:
        end = time.time()
        if upload_log:
            upload_log.add_log('process_country_selection_for_review',
                               end - start)
        action_data.on_finished(True, {
            'is_valid': False,
            'error': error
        })
        return
    ready_to_review_func = module_function(
        dataset.module.code_name,
        'prepare_review',
        'ready_to_review')
    ready_to_review_func(uploads)
    for upload in uploads:
        # Start the comparison boundary in the background
        celery_task = run_comparison_boundary.apply_async(
            (upload.id,),
            queue='validation'
        )
        upload.task_id = celery_task.id
        upload.save(update_fields=['task_id'])
    upload_session.update(status=REVIEWING)
    # remove entities from non-selected country
    non_selected_uploads = EntityUploadStatus.objects.filter(
        upload_session__in=upload_session
    ).exclude(
        id__in=upload_entity_ids
    )
    for upload in non_selected_uploads:
        if upload.revised_geographical_entity:
            revised = upload.revised_geographical_entity
            upload.revised_geographical_entity = None
            upload.save(update_fields=['revised_geographical_entity'])
            if revised:
                revised.delete()
    end = time.time()
    if upload_log:
        upload_log.add_log(
            'process_country_selection_for_review', end - start)
    action_data.on_finished(True, {
        'is_valid': True,
        'error': None
    })


@shared_task(name='run_comparison_boundary')
def run_comparison_boundary(entity_upload_id: int):
    from dashboard.models.entity_upload import (
        EntityUploadStatus,
        REVIEWING
    )
    from dashboard.models.notification import (
        Notification,
        NOTIF_TYPE_BOUNDARY_MATCHING
    )
    entity_upload = EntityUploadStatus.objects.get(
        id=entity_upload_id
    )
    dataset = entity_upload.upload_session.dataset

    upload_log, _ = EntityUploadStatusLog.objects.get_or_create(
        entity_upload_status=entity_upload,
        layer_upload_session=entity_upload.upload_session
    )
    prepare_review = module_function(
        dataset.module.code_name,
        'prepare_review',
        'prepare_review')
    prepare_review(
        entity_upload,
        **{'log_object': upload_log}
    )
    # send notifications only when all upload has been prepared
    has_pending_upload = EntityUploadStatus.objects.filter(
            upload_session=entity_upload.upload_session,
            status=REVIEWING,
            comparison_data_ready=False
    ).exists()
    if not has_pending_upload:
        message = (
            f'Boundary matching for {dataset.label}'
            ' has finished! Click here to view!'
        )
        payload = {
            'review_id': entity_upload.upload_session.id,
            'severity': 'success'
        }

        Notification.objects.create(
            type=NOTIF_TYPE_BOUNDARY_MATCHING,
            message=message,
            recipient=entity_upload.upload_session.uploader,
            payload=payload
        )


@shared_task(name='layer_upload_preprocessing')
def layer_upload_preprocessing(
    upload_session_id: int,
    log_object_id: int = None
):
    start = time.time()
    logger.info(
        'Running layer_upload_preprocessing '
        f'for session {upload_session_id}'
    )
    upload_log = None
    if log_object_id:
        upload_log = EntityUploadStatusLog.objects.get(
            id=log_object_id
        )

    upload_session = LayerUploadSession.objects.get(
        id=upload_session_id
    )
    dataset = upload_session.dataset
    prepare_validation = module_function(
        dataset.module.code_name,
        'upload_preprocessing',
        'prepare_validation')
    kwargs = {
        'log_object': upload_log
    }
    prepare_validation(
        upload_session,
        **kwargs
    )
    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log(
            'layer_upload_preprocessing',
            end - start
        )


@shared_task(name='delete_layer_upload_session')
def delete_layer_upload_session(session_id):
    upload_session = LayerUploadSession.objects.get(id=session_id)
    all_uploads = upload_session.entityuploadstatus_set.all()
    upload: EntityUploadStatus
    for upload in all_uploads:
        if upload.error_report:
            if (
                not upload.error_report.storage.exists(
                    upload.error_report.name)
            ):
                upload.error_report = None
                upload.save(update_fields=['error_report'])
    uploads = upload_session.entityuploadstatus_set.exclude(
        revised_geographical_entity__isnull=True
    )
    for upload in uploads:
        # delete revised entity level 0
        upload.revised_geographical_entity.delete()
    layer_files = upload_session.layerfile_set.all()
    layer_file: LayerFile
    for layer_file in layer_files:
        # check exist layer_file.layer_file, if not, then set to null
        if layer_file.layer_file:
            if (
                not layer_file.layer_file.storage.exists(
                    layer_file.layer_file.name)
            ):
                layer_file.layer_file = None
                layer_file.save(update_fields=['layer_file'])
        # layer_file FK is not set to cascade
        # need to manually delete
        GeographicalEntity.objects.filter(
            layer_file=layer_file
        ).delete()
    upload_session.delete()


@shared_task(name='reset_upload_session')
def reset_upload_session(session_id, preprocessing, qc_validation, cancel):
    """Reset step or cancel upload."""
    logger.info(
        'Running reset_upload_session '
        f'for session {session_id}: preprocessing {preprocessing} '
        f'qc_validation {qc_validation} cancel {cancel}'
    )
    upload_session = LayerUploadSession.objects.get(id=session_id)
    # cancel all running task in entity upload status
    uploads = upload_session.entityuploadstatus_set.all()
    for upload in uploads:
        if upload.task_id:
            cancel_task(upload.task_id, force=True)
    if qc_validation:
        reset_func = module_function(
            upload_session.dataset.module.code_name,
            'qc_validation',
            'reset_qc_validation'
        )
        reset_func(upload_session)
    if preprocessing:
        reset_func = module_function(
            upload_session.dataset.module.code_name,
            'upload_preprocessing',
            'reset_preprocessing'
        )
        reset_func(upload_session)
    if cancel and not preprocessing:
        reset_func = module_function(
            upload_session.dataset.module.code_name,
            'upload_preprocessing',
            'reset_preprocessing'
        )
        reset_func(upload_session)
    logger.info(
        'Finished reset_upload_session '
        f'for session {session_id}: preprocessing {preprocessing} '
        f'qc_validation {qc_validation} cancel {cancel}'
    )


@shared_task(name='patch_summaries_stat_by_upload_session')
def patch_summaries_stat_by_upload_session(session_id):
    upload_session = LayerUploadSession.objects.get(id=session_id)
    dataset = upload_session.dataset
    count_error_categories_func = module_function(
        dataset.module.code_name,
        'qc_validation',
        'count_error_categories')
    all_uploads = upload_session.entityuploadstatus_set.all()
    upload: EntityUploadStatus
    for upload in all_uploads:
        if upload.summaries:
            (
                allowable_errors, blocking_errors,
                superadmin_bypass_errors,
                superadmin_blocking_errors
            ) = count_error_categories_func(upload.summaries)
            upload.allowable_errors = allowable_errors
            upload.blocking_errors = blocking_errors
            upload.superadmin_bypass_errors = superadmin_bypass_errors
            upload.superadmin_blocking_errors = superadmin_blocking_errors
            upload.save(update_fields=[
                'allowable_errors', 'blocking_errors',
                'superadmin_bypass_errors', 'superadmin_blocking_errors'
            ])
