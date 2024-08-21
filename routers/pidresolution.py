from celery import group
from fastapi import APIRouter
from starlette.responses import JSONResponse

from api import pidresolver
from celeryworker.tasks import resolve_all_pids_task, resolve_pid_task
from celeryworker.utils import get_task_info
from schemas.schemas import Pid
from settings import settings

router = APIRouter(responses={404: {"description": "Not found"}}, tags=["PID Resolution"])

MAX_CELERY_GROUP_SIZE = settings.CELERY_MAX_GROUP_SIZE


@router.post("/pid/")
def get_pid_status_codes(pid: Pid) -> dict:
    """
    Return the List of HTTP response codes in a sync way
    """
    data: dict = {}
    for pid in pid.pids:
        data.update(pidresolver.resolve_url_by_pid(pid))
    return data


@router.post("/pid/parallel")
async def get_status_codes(pid: Pid) -> dict:
    """
    This uses Celery to perform subtasks in a parallel manner. For each Celery canvas group it creates, it creates one task, that should be picked up by a worker.
    """
    subpidlists = [pid.pids[i:i + MAX_CELERY_GROUP_SIZE]
                   for i in range(0, len(pid.pids), MAX_CELERY_GROUP_SIZE)]

    for groupchunk in subpidlists:
        tasks = [resolve_pid_task.s(pit) for pit in groupchunk]
        job = group(tasks)
        job.apply_async()

    result = {
        "PIDs added to the queue": len(pid.pids),
        "Created tasks in parallel": len(subpidlists),
        "Max group size:": MAX_CELERY_GROUP_SIZE
    }
    return result


@router.post("/pid/async")
async def get_status_codes_async(pid: Pid):
    """Creates one task for all provided PIDs. It is picked up by only ONE worker..."""
    task_result = resolve_all_pids_task.apply_async(args=[pid.pids])
    return JSONResponse({"task_id": task_result.id})


@router.get("/task/{task_id}", tags=["Celery"])
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of a Celery TaskId
    """
    return get_task_info(task_id)
