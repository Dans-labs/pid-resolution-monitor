import random
from datetime import datetime, timedelta, timezone
from typing import List

import httpx
from celery import shared_task, Task

from api import pidresolver
from database.crud import save_pid_resolution_results, add_pidmr_resolution_event
from logging_config import prm_logger as logger


# @shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 1},
#              name='pidmr:save_pidmr_event_task', ignore_result=True)
# def save_pidmr_event_task(self, event: PidMrEventRecord):
#     store_result = pidmr.save_pidmr_event(event)
#     return store_result


def _get_new_eta() -> datetime:
    base_eta = datetime.now(timezone.utc) + timedelta(hours=24) # 24 hours
    jitter_seconds = random.randint(-3600, 3600)
    # base_eta = datetime.now(timezone.utc) + timedelta(seconds=20)
    # jitter_seconds = random.randint(-3, 3)
    jittered_eta = base_eta + timedelta(seconds=jitter_seconds)
    return jittered_eta


class BaseResolutionTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        rr = pidresolver.create_resolution_record(
            args[0],
            pidresolver.get_actionable_pid_url(args[0]),
            None,
            False,
            str(exc)
        )

        save_pid_resolution_results(record=rr, pid_type=args[1], batch_id=args[2])
        logger.warn(f"'{args[0]}' unresolvable after {self.request.retries}/{self.max_retries} retries. Error: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            f'Task {task_id} succeeded: {retval.pid_url} => {retval.resolution_url} (HTTP {retval.status_code})')


class BasePIDMRResolutionTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        rr = pidresolver.create_resolution_record(
            args[0],
            pidresolver.get_actionable_pid_url(args[0]),
            None,
            False,
            str(exc)
        )
        # save_pid_resolution_results(record=rr, pid_type=args[1], batch_id=1)
        pid_resolution_id = save_pid_resolution_results(record=rr, pid_type=args[1], batch_id=1).id
        add_pidmr_resolution_event(args[2], pid_resolution_id)

        logger.warn(f"'{args[0]}' unresolvable after {self.request.retries}/{self.max_retries} retries. Error: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            f'Task {task_id} succeeded: {retval.pid_url} => {retval.resolution_url} (HTTP {retval.status_code})')


@shared_task(bind=True, autoretry_for=(httpx.HTTPError,), name='pid-resolution:resolve_pid_task',
             base=BaseResolutionTask, ignore_result=True,
             throws=(httpx.HTTPError,), max_retries=1)
def resolve_pid_task(self, pid: str, pid_type: str, batch_id: int):
    try:
        logger.info(f"Starting PID resolution TASK for: {pid} ({self.request.retries}/{self.max_retries})")
        resolution_record = pidresolver.resolve_url_by_pid(pid)
        save_pid_resolution_results(record=resolution_record, batch_id=batch_id, pid_type=pid_type)
        return resolution_record
    except httpx.HTTPError as e:
        logger.debug(f"PID {pid} resolution failed. retries: {self.request.retries}/{self.max_retries}, Error: {e}.")
        raise self.retry(exc=e, queue='celery', max_retries=1, eta=_get_new_eta())


@shared_task(bind=True, autoretry_for=(httpx.HTTPError,), name='pid-resolution:resolve_pidmr_task',
             base=BasePIDMRResolutionTask, ignore_result=True,
             throws=(httpx.HTTPError,), max_retries=1)
def resolve_pidmr_task(self, pid: str, pid_type: str, pidmr_event_id: int):
    try:
        logger.info(f"Starting PIDMR PID resolution TASK for: {pid} ({self.request.retries}/{self.max_retries})")
        resolution_record = pidresolver.resolve_url_by_pid(pid,
                                                           is_actionable=True)  # Resolve actionable PID URL as supplied by PIDMR.
        pid_resolution_id = save_pid_resolution_results(record=resolution_record, batch_id=1, pid_type=pid_type).id
        add_pidmr_resolution_event(pidmr_event_id, pid_resolution_id)
        return resolution_record
    except httpx.HTTPError as e:
        logger.debug(
            f"PID {pid} resolution for PIDMR failed. retries: {self.request.retries}/{self.max_retries}, Error: {e}.")
        raise self.retry(exc=e, queue='celery', max_retries=1, eta=_get_new_eta())


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 1},
             name='pid-resolution:resolve_all_pids_task')
def resolve_all_pids_task(self, pides: List[str]):
    data: dict = {}
    for pidx in pides:
        data.update(pidresolver.resolve_url_by_pid(pidx))
    return data
