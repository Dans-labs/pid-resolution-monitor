from typing import List

from celery import shared_task
from fastapi import Depends
from sqlalchemy.orm import Session

from api import pidresolver, pidmr
from database.crud import save_pid_resolution_record
from database.database import get_db
from schemas.schemas import PIDMResolutionEvent


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, name='pidmr:save_pidmr_event_task')
def save_pidmr_event_task(self, event: PIDMResolutionEvent):
    store_result = pidmr.save_pidmr_event(event)
    return store_result


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name='pid-resolution:resolve_pid_task')
def resolve_pid_task(self, pidx: str):
    resolution_record = pidresolver.get_resolved_pid_status_code(pidx)
    save_pid_resolution_record(record=resolution_record)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}, name='pid-resolution:resolve_all_pids_task')
def resolve_all_pids_task(self, pides: List[str]):
    data: dict = {}
    for pidx in pides:
        data.update(pidresolver.get_resolved_pid_status_code(pidx))
    return data
