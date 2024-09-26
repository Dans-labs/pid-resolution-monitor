from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from celeryworker.tasks import resolve_pid_task
from database.crud import create_pidmr_event
from database.database import get_db
from database.models import PIDMREvent
from logging_config import pidmr_logger as logger
from routers.users import get_current_enabled_user
from schemas.schemas import PidMrResolutionEvent, User

router = APIRouter(
    prefix="/pidmr",
    tags=["PIDMR"],
    responses={404: {"description": "Not found"}},
)


@router.post("/event", response_model=PidMrResolutionEvent, summary="Registers a PIDMR event.",
             description="Creates a PIDMR event and starts PID resolution for the provided PID in the background. The returned 'pidmr_event_id' can be used to track the resolution status.")
async def create_event(event: PidMrResolutionEvent, user: Annotated[User, Depends(get_current_enabled_user)],
                       db: Session = Depends(get_db)):
    try:
        db_event = create_pidmr_event(db=db, event=event)
        if not db_event:
            raise HTTPException(status_code=400, detail="Error saving event")  # 400 to 499 are client error codes.
        logger.info(
            f"PIDMR event saved: {db_event.pid_endpoint} by user {user.username}")  # TODO: determine what to log.
        # Create a celery task to resolve this PID:
        try:
            resolve_pid_task.delay(db_event.pid_endpoint)
        except Exception as e:
            logger.error(f"Error starting PID resolution Celery task for PIDMR Event ID: {db_event.id}. Error: {e}")
        return PidMrResolutionEvent(id=db_event.id, time_stamp=db_event.time_stamp, pid_id=db_event.pid_id,
                                    pid_mode=db_event.pid_mode, pid_type=db_event.pid_type,
                                    pid_endpoint=db_event.pid_endpoint,
                                    pid_resolver_status=db_event.pid_resolver_status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@router.get("/event/{pidmr_event_id}", response_model=PidMrResolutionEvent,
            summary="Get registered PIDMR Event by PIDMR Event ID", dependencies=[Depends(get_current_enabled_user)])
def get_pid_resolution_record(pidmr_event_id: int, db: Session = Depends(get_db)):
    """
    Gets the PidMrResolutionEvent by pidmr_event_id.
    """
    record = db.query(PIDMREvent).filter(PIDMREvent.id == pidmr_event_id).first()
    if not record:
        raise HTTPException(status_code=404,
                            detail=f"PIDMR Event record not found for PIDMR Event ID: {pidmr_event_id}")
    return record
