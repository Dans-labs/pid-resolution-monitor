from typing import List

from celery import shared_task

from api import pidresolver, pidmr
from schemas.schemas import PIDMRRootSchema


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, name='pidmr:save_pidmr_event_task')
def save_pidmr_event_task(self, event: PIDMRRootSchema):
    store_result = pidmr.save_pidmr_event(event)
    return store_result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, name='pid-resolution:resolve_pid_task')
def resolve_pid_task(self, pidx: str):
    http_status = pidresolver.get_resolved_pid_status_code(pidx)
    return http_status


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, name='pid-resolution:resolve_all_pids_task')
def resolve_all_pids_task(self, pides: List[str]):
    data: dict = {}
    for pidx in pides:
        data.update(pidresolver.get_resolved_pid_status_code(pidx))
    return data
