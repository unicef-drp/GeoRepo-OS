import requests
import logging
from ast import literal_eval as make_tuple
from celery.result import AsyncResult
from core.celery import app
from georepo.models.background_task import BackgroundTask
from georepo.models.dataset_view import (
    DatasetView,
    DatasetViewResource
)


logger = logging.getLogger(__name__)

REST_URL = (
    'http://worker:8080/flower/api/task/info/'
)
TASK_NOT_FOUND = 'NOT FOUND'


def get_task_status(task_id: str):
    """Fetch task status from Flower API"""
    status = None
    try:
        response = requests.get(f'{REST_URL}{task_id}')
        if response.status_code == 404:
            # when the task is not found, means:
            # - task is not sent to worker yet
            # - running task but got interupted
            # - too old task that has been removed after success/failure
            status = TASK_NOT_FOUND
        else:
            detail = response.json()
            # possible STATE: 'PENDING', 'RECEIVED',
            # 'STARTED', 'SUCCESS', 'FAILURE',
            status = detail['state'] if 'state' in detail else ''
    except requests.exceptions.ConnectionError as errc:
        logger.error('Error connect : ', errc)
        raise RuntimeError('Unable to connect to Worker Flower API!')
    return status


def on_task_queued_or_running(task: BackgroundTask):
    task_param = make_tuple(task.parameters or '()')
    if task.name == 'generate_view_resource_vector_tiles_task':
        if len(task_param) == 0:
            return
        view_resource_id = task_param[0]
        resource = DatasetViewResource.objects.get(
            id=view_resource_id)
        resource.tiling_current_task = task
        resource.save(update_fields=['tiling_current_task'])
    elif task.name == 'view_simplification_task':
        if len(task_param) == 0:
            return
        view_id = task_param[0]
        view = DatasetView.objects.get(id=view_id)
        view.simplification_current_task = task
        view.save(update_fields=['simplification_current_task'])


def on_task_success(task: BackgroundTask):
    task_param = make_tuple(task.parameters or '()')
    if task.name == 'generate_view_resource_vector_tiles_task':
        if len(task_param) == 0:
            return
        view_resource_id = task_param[0]
        resource = DatasetViewResource.objects.get(
            id=view_resource_id)
        resource.tiling_current_task = None
        resource.save(update_fields=['tiling_current_task'])
    elif task.name == 'view_simplification_task':
        if len(task_param) == 0:
            return
        view_id = task_param[0]
        view = DatasetView.objects.get(id=view_id)
        view.simplification_current_task = None
        view.save(update_fields=['simplification_current_task'])


def cancel_task(task_id: str):
    try:
        res = AsyncResult(task_id)
        if not res.ready():
            # find if there is running task and stop it
            app.control.revoke(
                task_id,
                terminate=True,
                signal='SIGKILL'
            )
    except Exception as ex:
        logger.error(f'Failed cancel_task: {task_id}')
        logger.error(ex)
