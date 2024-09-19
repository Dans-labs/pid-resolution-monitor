import random
import httpx

from datetime import datetime, timedelta, timezone
from typing import List
from celery import shared_task, Task
from api import pidresolver, pidmr
from database.crud import save_pid_resolution_record
from logging_config import prm_logger as logger
from schemas.schemas import PIDMResolutionEvent


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 1},
             name='pidmr:save_pidmr_event_task', ignore_result=True)
def save_pidmr_event_task(self, event: PIDMResolutionEvent):
    store_result = pidmr.save_pidmr_event(event)
    return store_result


class BaseResolutionTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        rr = pidresolver.create_resolution_record(
            args[0],
            pidresolver.get_actionable_pid_url(args[0]),
            None,
            False,
            str(exc)
        )
        save_pid_resolution_record(record=rr)
        logger.warn(f"'{args[0]}' unresolvable after {self.request.retries}/{self.max_retries} retries. Error: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f'Task {task_id} succeeded: {retval.pid_url} => {retval.resolution_url} (HTTP {retval.status_code})')


@shared_task(bind=True, autoretry_for=(httpx.HTTPError,), name='pid-resolution:resolve_pid_task',
             base=BaseResolutionTask, ignore_result=True,
             throws=(httpx.HTTPError,), max_retries=1)
def resolve_pid_task(self, pid: str):
    try:
        logger.info(f"Starting PID resolution TASK for: {pid} ({self.request.retries}/{self.max_retries})")
        resolution_record = pidresolver.resolve_url_by_pid(pid)
        save_pid_resolution_record(record=resolution_record)
        return resolution_record
    except httpx.HTTPError as e:
        logger.debug(f"PID {pid} resolution failed. retries: {self.request.retries}/{self.max_retries}, Error: {e}.")
        base_eta = datetime.now(timezone.utc) + timedelta(hours=24)
        jitter_seconds = random.randint(-3600, 3600)
        jittered_eta = base_eta + timedelta(seconds=jitter_seconds)
        raise self.retry(exc=e, queue='celery', max_retries=1, eta=jittered_eta)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 1},
             name='pid-resolution:resolve_all_pids_task')
def resolve_all_pids_task(self, pides: List[str]):
    data: dict = {}
    for pidx in pides:
        data.update(pidresolver.resolve_url_by_pid(pidx))
    return data
