from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.crud import create_pidmr_event
from database.database import get_db
from logging_config import pidmr_logger as logger
from schemas import schemas

router = APIRouter(
    prefix="/pidmr",
    tags=["PIDMR"],
    responses={404: {"description": "Not found"}},
)

@router.post("/event")
def create_event(event: schemas.PIDMResolutionEvent, db: Session = Depends(get_db)):
    try:
        db_event = create_pidmr_event(db=db, event=event)
        if not db_event:
            raise HTTPException(status_code=400, detail="Error saving event") #400 to 499 are client error codes.
        logger.info(f"PIDMR event saved: {db_event.pid_endpoint}")
        # TODO: Add a celery task to resolve the PID
        return {"event_id": db_event.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server errort: {e}")
