from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from celeryworker.tasks import resolve_pidmr_task
from database.crud import create_pidmr_event, get_pid_resolution_percentage_by_batch_id
from database.database import get_db
from database.models import PIDMREvent, MonitorRecord, PIDMRResolution
from logging_config import pidmr_logger as logger
from routers.users import get_current_enabled_user
from schemas.schemas import PidMrEventRecord, User, PidResolutionRecord

router = APIRouter(
    prefix="/pidmr",
    tags=["PIDMR"],
    responses={404: {"description": "Not found"}},
)


@router.post("/event", response_model=PidMrEventRecord, summary="Registers a PIDMR event.",
             description="Creates a PIDMR event and starts PID resolution for the provided PID in the background. The returned 'id' (pidmr_event_id), can be used to track the resolution status later.")
async def create_event(event: PidMrEventRecord, user: Annotated[User, Depends(get_current_enabled_user)],
                       db: Session = Depends(get_db)):
    # Dit event wordt geregistreerd in de pidmr_events tabel. De resolutie resultaten moeten worden opgeslagen in de pid_resolution tabel met batch_id=1 en pid_url dient de aangeleverde pid_mr endpoint te zijn.
    try:
        db_event = create_pidmr_event(event=event, db=db)  # Stores the PIDMR event in the pidmr_events tabel.
        if not db_event:
            raise HTTPException(status_code=400,
                                detail="Error saving PIDMR event")  # 400 to 499 are client error codes.
        logger.info(
            f"PIDMR event {db_event.id} saved: {db_event.pid_endpoint} by user {user.username}")
        try:  # Create a celery task to resolve PID and store the results: The task needs the batch_id (which is always "1" for PIDMR), the pid_type and the pid_endpoint.
            resolve_pidmr_task.delay(db_event.pid_endpoint, db_event.pid_type, db_event.id)
        except Exception as e:
            logger.error(f"Error starting PID resolution Celery task for PIDMR Event ID: {db_event.id}. Error: {e}")
        return PidMrEventRecord(id=db_event.id, time_stamp=db_event.time_stamp, pid_id=db_event.pid_id,
                                pid_mode=db_event.pid_mode, pid_type=db_event.pid_type,
                                pid_endpoint=db_event.pid_endpoint,
                                pid_resolver_status=db_event.pid_resolver_status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@router.get("/event/{pidmr_event_id}", response_model=PidMrEventRecord,
            summary="Get registered PIDMR Event by PIDMR Event ID", dependencies=[Depends(get_current_enabled_user)])
def get_pidmr_event_record(pidmr_event_id: int, db: Session = Depends(get_db)):
    """
    Gets the PidMR Event by pidmr_event_id.
    """
    record = db.query(PIDMREvent).filter(
        PIDMREvent.id == pidmr_event_id).first()  # TODO: refactor, add to crud and call a function to get PIDMR event by ID.
    if not record:
        raise HTTPException(status_code=404,
                            detail=f"PIDMR Event record not found for PIDMR Event ID: {pidmr_event_id}")
    return record


# TODO: refactor db stuff to crud.py
@router.get("/resolution/{pidmr_event_id}",
            response_model=PidResolutionRecord,
            summary="Get PID resolution results by PIDMR Event ID",
            dependencies=[Depends(get_current_enabled_user)])
def get_pidmr_resolution_record(pidmr_event_id: int, db: Session = Depends(get_db)):
    """
    Gets the PidMResolutionRecord by pidmr_event_id.
    """
    # record = db.query(MonitorRecord).filter(MonitorRecord.id == pidmr_event_id).first()
    record = db.query(MonitorRecord).join(PIDMRResolution, MonitorRecord.id == PIDMRResolution.resolution_id).filter(
        PIDMRResolution.pidmr_event_id == pidmr_event_id).first()
    if not record:
        raise HTTPException(status_code=404,
                            detail=f"PIDMR Event record not found for PIDMR Event ID: {pidmr_event_id}")
    pid_resolution_record = PidResolutionRecord(

        time_stamp=record.time_stamp,
        pid_id=str(record.pid_id),
        pid_url=str(record.pid_url),
        status_code=record.status_code or None,
        content_type=record.content_type or None,
        ssl_verified=bool(record.ssl_verified),
        redirect_count=record.redirect_count or None,
        resolution_url=record.resolution_url or None,
        http_error=str(record.http_error) or None

    )
    return pid_resolution_record


@router.get("/resolution",
            response_model=dict,
            summary="Get PID resolution percentage over all registered PIDMR Events.",
            dependencies=[Depends(get_current_enabled_user)])
def get_pidmr_resolution_percentage(db: Session = Depends(get_db)):
    """
    Test 35 (pid_graph:E54B2EEA): "Resolution Percentage"
    The test involves determining the percentage f of resolved PIDs that result in a viable entity, compared to a community expectation p.
    """
    resolution_percentage = get_pid_resolution_percentage_by_batch_id(1, db)
    return resolution_percentage


# @router.get("/pid/{pid_resolution_id}", response_model=PidResolutionRecord,
#             summary="Get the PID Resolution results by PIDMR Event ID")
# def get_pid_resolution_record(pid_resolution_id: int, db: Session = Depends(get_db)):
#     """
#     Gets the PidResolutionRecord by pidmr_event_id.
#     """
#     record = db.query(MonitorRecord).filter(MonitorRecord.id == pid_resolution_id).first()
#     if not record:
#         raise HTTPException(status_code=404,
#                             detail=f"PidResolutionRecord not found for PIDMR Event ID: {pid_resolution_id}")
#     return record
