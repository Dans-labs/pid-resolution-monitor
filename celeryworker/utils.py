from celery import current_app as current_celery_app
from celery.result import AsyncResult

from .config import settings


def create_celery():
    celery_app = current_celery_app
    celery_app.config_from_object(settings, namespace='CELERY')
    celery_app.conf.update(task_track_started=True)
    celery_app.conf.update(task_serializer='json')
    celery_app.conf.update(result_serializer='pickle')
    celery_app.conf.update(accept_content=['json', 'pickle'])
    # celery_app.conf.update(result_persistent=True) # defaults to False
    celery_app.conf.update(worker_send_task_events=False)
    celery_app.conf.update(worker_prefetch_multiplier=1)
    celery_app.conf.update(broker_connection_retry_on_startup=True)

    return celery_app


def get_task_info(task_id):
    """
    return task info for the given task_id
    """
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return result
