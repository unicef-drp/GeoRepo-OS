import requests
import logging


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
