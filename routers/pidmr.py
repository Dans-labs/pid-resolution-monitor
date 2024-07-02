from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.crud import create_pidmr_event
from database.database import get_db
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
            raise HTTPException(status_code=400, detail="Error saving event")
        return {"event_id": db_event.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server errort: {e}")
