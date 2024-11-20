from typing import Annotated

import sqlalchemy
from celery import group
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from celeryworker.tasks import resolve_pid_task
from database.crud import insert_pid_resolution_batch, get_pid_resolution_batch, update_pid_resolution_batch, \
    get_pidslist_for_batch, get_total_pids_by_batch
from database.database import get_db
from routers.users import get_current_enabled_user, get_current_user
from schemas.schemas import PidResolutionCreateBatch, PidResolutionUpdateBatch, User, \
    BatchPids, PidBaseBatch, PidUpdateBatch
from settings import settings

# TODO: Decide on format for error response messages (json or text).

MAX_CELERY_GROUP_SIZE = settings.CELERY_MAX_GROUP_SIZE

router = APIRouter(responses={404: {"description": "Not found"}}, dependencies=[Depends(get_current_enabled_user)],
                   tags=["PID Resolution"], prefix="/pid")


# @router.post("/", response_model=dict,
#              summary="Get the HTTP response codes for a list of PIDs.")
# def get_pid_status_codes(pid: Pid) -> dict:
#     """
#     Return a List of HTTP response codes in a sync way. Does not persist the results.
#     """
#     data: dict = {}
#     for pid in pid.pids:
#         data[pid] = pidresolver.resolve_url_by_pid(pid).status_code
#     return data


@router.post("/batch", status_code=201,
             response_model=PidBaseBatch,
             responses={409: {"description": "Conflict", "content": {
                 "application/json": {"example": {"detail": "Conflict: Batch already exists."}}}}},
             summary="Create a new PID batch for PID resolution.",
             description="Creates a new PID batch with PIDs that will be resolved. To add additional PIDs to an existing batch, use the '/pid/batch/update' endpoint. You will need the batch_id, amongst other properties, to do so.")
def create_pid_resolution_sample(sample: PidResolutionCreateBatch,
                                 current_user: Annotated[User, Depends(get_current_user)],
                                 db: Session = Depends(get_db)) -> PidBaseBatch:
    try:
        batch_id = insert_pid_resolution_batch(sample, current_user.username, db)
        # This uses Celery to perform subtasks in a PARALLEL manner. For each Celery canvas group it creates, it creates one task, that will be picked up by a worker.
        subpidlists = [sample.sample_pids[i:i + MAX_CELERY_GROUP_SIZE] for i in
                       range(0, len(sample.sample_pids), MAX_CELERY_GROUP_SIZE)]

        for groupchunk in subpidlists:
            tasks = [resolve_pid_task.s(pit, sample.identifier_type, batch_id) for pit in groupchunk]
            job = group(tasks)
            job.apply_async()

        return PidBaseBatch(
            batch_id=batch_id,
            total_pids=len(sample.sample_pids),
            identifier_type=sample.identifier_type,
            actor=sample.actor,
            institution=sample.institution,
            description=sample.description
        )
    except sqlalchemy.exc.IntegrityError as e:
        raise HTTPException(status_code=409, detail=e.orig.diag.message_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}", response_model=PidBaseBatch,
            summary="Gets an existing PID batch by it's batch_id.")
def get_pid_resolution_sample(batch_id: int, db: Session = Depends(get_db)) -> PidBaseBatch:
    try:
        batch_ = get_pid_resolution_batch(batch_id, db)
        if not batch_:
            raise HTTPException(status_code=404, detail=f"Batch id: {batch_id} not found.")
        return batch_
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/batch/update",
            summary="Add PID's to an existing PID batch by it's batch_id.",
            description="The PID types, Actor and Instititute should be the same as the original PID batch.",
            response_model=PidUpdateBatch,
            responses={400: {"description": "Bad Request", "content": {"application/json": {
                "example": {"detail": "Invalid data submitted: No matching batch found for provided parameters."}}}}})
def update_pid_resolution_sample(batch: PidResolutionUpdateBatch, db: Session = Depends(get_db)) -> PidUpdateBatch:
    try:
        if len(batch.sample_pids) == 0:
            raise HTTPException(status_code=400, detail="Invalid data submitted: No PIDs provided.")
        added_pids = update_pid_resolution_batch(batch, db)  # Actual PIDs added to the batch. Needed for resolution.
        if added_pids is False:
            raise HTTPException(status_code=400,
                                detail="Invalid data submitted: No matching batch found for provided parameters.")
        total_pids = get_total_pids_by_batch(batch.id, db)

        # Schedule Celery tasks to resolve the PIDs in the updated batch.
        # for pid in added_pids:
        #    resolve_pid_task.delay(pid, batch.identifier_type, batch.id)

        # This uses Celery to perform subtasks in a PARALLEL manner. For each Celery canvas group it creates, it creates one task, that will be picked up by a worker.
        subpidlists = [added_pids[i:i + MAX_CELERY_GROUP_SIZE] for i in
                       range(0, len(added_pids), MAX_CELERY_GROUP_SIZE)]

        for groupchunk in subpidlists:
            tasks = [resolve_pid_task.s(pit, batch.identifier_type, batch.id) for pit in groupchunk]
            job = group(tasks)
            job.apply_async()

        return PidUpdateBatch(
            batch_id=batch.id,
            pids_added=len(added_pids),
            total_pids=total_pids,
            identifier_type=batch.identifier_type,
            actor=batch.actor,
            institution=batch.institution
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pids/{batch_id}", response_model=BatchPids, summary="Retrieve PIDs for a specific batch",
            description="Get a paginated list of PIDs for a specific batch. The limit parameter specifies the number of items to return per page (1 - 1000), and the offset parameter specifies the starting point for the items to return.")
def get_pids(batch_id: int, limit: int = Query(250, ge=1, le=1000), offset: int = Query(0, ge=0),
             db: Session = Depends(get_db)) -> BatchPids:
    """
    Get a paginated list of PIDs for a specific batch.
    - batch_id: The ID of the batch to retrieve PIDs from.
    - limit: Number of items to return per page (default is 250).
    - offset: Starting point for the items to return (default is 0).
    """

    total_pids = get_total_pids_by_batch(batch_id, db)
    pids_ = get_pidslist_for_batch(batch_id, limit, offset, db)
    if not pids_:
        raise HTTPException(status_code=404, detail=f"No PIDs found for batch_id: {batch_id}")

    return BatchPids(
        batch_id=batch_id,
        total_pids=total_pids,
        limit=limit,
        offset=offset,
        pids=pids_
    )

# @router.post("/parallel", response_model=dict, include_in_schema=False)
# async def get_status_codes(pid: Pid) -> dict:
#     """
#     This uses Celery to perform subtasks in a parallel manner. For each Celery canvas group it creates, it creates one task, that should be picked up by a worker.
#     """
#     subpidlists = [pid.pids[i:i + MAX_CELERY_GROUP_SIZE]
#                    for i in range(0, len(pid.pids), MAX_CELERY_GROUP_SIZE)]
#
#     for groupchunk in subpidlists:
#         tasks = [resolve_pid_task.s(pit) for pit in groupchunk]
#         job = group(tasks)
#         job.apply_async()
#
#     result = {
#         "PIDs added to the queue": len(pid.pids),
#         "Created tasks in parallel": len(subpidlists),
#         "Max group size:": MAX_CELERY_GROUP_SIZE
#     }
#     return result
#
#
# @router.post("/async", include_in_schema=False)
# async def get_status_codes_async(pid: Pid):
#     """Creates one task for all provided PIDs. It is picked up by only ONE worker..."""
#     task_result = resolve_all_pids_task.apply_async(args=[pid.pids])
#     return JSONResponse({"task_id": task_result.id})
