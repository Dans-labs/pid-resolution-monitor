from celery import group
from dynaconf import Dynaconf
from fastapi import APIRouter
from starlette.responses import JSONResponse

from api import pidresolver
from celery_tasks.tasks import resolve_pid_task, resolve_all_pids_task, save_pidmr_event_task
from config.celery_utils import get_task_info
from schemas.schemas import PIDMRRootSchema, Pid

router = APIRouter(responses={404: {"description": "Not found"}})
settings = Dynaconf(settings_files=["config/settings.toml"], secrets=["config/.secrets.toml"], environments=True, default_env="default", load_dotenv=True)

MAX_CELERY_GROUP_SIZE = settings.MAX_CELERY_GROUP_SIZE


@router.post("/pid/", tags=["PID Resolution"])
def get_pid_status_codes(pid: Pid) -> dict:
    """
    Return the List of HTTP response codes in a sync way
    """
    data: dict = {}
    for pidx in pid.pids:
        data.update(pidresolver.get_resolved_pid_status_code(pidx))
    return data


@router.post("/pid/parallel", tags=["PID Resolution"])
async def get_status_codes(pid: Pid) -> dict:
    """
    This uses Celery to perform subtasks in a parallel manner. For each Celey canvas group it creates, it creates one task, that should be picked up by a worker.
    """

    subpidlists = [pid.pids[i:i + MAX_CELERY_GROUP_SIZE] for i in range(0, len(pid.pids), MAX_CELERY_GROUP_SIZE)]

    for groupchunk in subpidlists:
        tasks = []
        for pit in groupchunk:
            tasks.append(resolve_pid_task.s(pit))
        # create a group to run in parralel for these tasks
        job = group(tasks)
        job.apply_async()

    result = {
        "PIDs added to the queue": len(pid.pids),
        "Created tasks in parallel": len(subpidlists),
        "Max group size:": MAX_CELERY_GROUP_SIZE
    }
    return result


# This endpoint creates one task for all provided PIDs. It is picked up by only ONE worker...
@router.post("/pid/async", tags=["PID Resolution"])
async def get_status_codes_async(pid: Pid):
    task_result = resolve_all_pids_task.apply_async(args=[pid.pids])
    return JSONResponse({"task_id": task_result.id})


@router.post("/pidmr/events", tags=["PIDMR"])
async def submit_events(content: PIDMRRootSchema):
    task_result = save_pidmr_event_task.apply_async(args=[content])
    return JSONResponse({"task_id": task_result.id})


@router.get("/task/{task_id}", tags=["Celery"])
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of a submitted TaskId
    """
    return get_task_info(task_id)