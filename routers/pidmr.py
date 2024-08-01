from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.crud import create_pidmr_event
from database.database import get_db
from logging_config import pidmr_logger as logger
from routers.users import get_current_enabled_user
from schemas.schemas import PIDMResolutionEvent, User

router = APIRouter(
    prefix="/pidmr",
    tags=["PIDMR"],
    responses={404: {"description": "Not found"}},
)


@router.post("/event")
async def create_event(event: PIDMResolutionEvent, user: Annotated[User, Depends(get_current_enabled_user)],
                       db: Session = Depends(get_db)):
    try:
        db_event = create_pidmr_event(db=db, event=event)
        if not db_event:
            raise HTTPException(status_code=400, detail="Error saving event")  # 400 to 499 are client error codes.
        logger.info(f"PIDMR event saved: {db_event.pid_endpoint} by user {user.username}")
        return {"event_id": db_event.id, "pid_endpoint": db_event.pid_endpoint}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
