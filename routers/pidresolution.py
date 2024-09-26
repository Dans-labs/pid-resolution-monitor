from typing import Annotated

from celery import group
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from api import pidresolver
from celeryworker.tasks import resolve_all_pids_task, resolve_pid_task
from celeryworker.utils import get_task_info
from database.database import get_db
from database.models import MonitorRecord
from routers.users import get_current_enabled_user
from schemas.schemas import Pid, User, PidResolutionRecord
from settings import settings

router = APIRouter(responses={404: {"description": "Not found"}})

MAX_CELERY_GROUP_SIZE = settings.CELERY_MAX_GROUP_SIZE
PID_RESOLUTION_TAG = "PID Resolution"

@router.post("/pid/", tags=[PID_RESOLUTION_TAG])
def get_pid_status_codes(pid: Pid, user: Annotated[User, Depends(get_current_enabled_user)]) -> dict:
    """
    Return the List of HTTP response codes in a sync way
    """
    data: dict = {}
    for pid in pid.pids:
        data[pid] = pidresolver.resolve_url_by_pid(pid).status_code
    return data


@router.post("/pid/parallel", tags=[PID_RESOLUTION_TAG])
async def get_status_codes(pid: Pid, user: Annotated[User, Depends(get_current_enabled_user)]) -> dict:
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


@router.post("/pid/async", tags=[PID_RESOLUTION_TAG])
async def get_status_codes_async(pid: Pid, user: Annotated[User, Depends(get_current_enabled_user)]):
    """Creates one task for all provided PIDs. It is picked up by only ONE worker..."""
    task_result = resolve_all_pids_task.apply_async(args=[pid.pids])
    return JSONResponse({"task_id": task_result.id})


@router.get("/pid/{pidmr_event_id}", tags=[PID_RESOLUTION_TAG], response_model=PidResolutionRecord, summary="Get the PID Resolution results by PIDMR Event ID")
def get_pid_resolution_record(pid_resolution_id: int, user: Annotated[User, Depends(get_current_enabled_user)], db: Session = Depends(get_db)):
    """
    Gets the PidResolutionRecord by pidmr_event_id.
    """
    record = db.query(MonitorRecord).filter(MonitorRecord.id == pid_resolution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"PidResolutionRecord not found for PIDMR Event ID: {pid_resolution_id}")
    return record



@router.get("/task/{task_id}", tags=["Celery"], summary="Get the status of a Celery Task")
async def get_task_status(task_id: str, user: Annotated[User, Depends(get_current_enabled_user)]) -> dict:
    """
    Return the status of a Celery TaskId
    """
    return get_task_info(task_id)
