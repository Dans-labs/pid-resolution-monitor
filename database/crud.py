from sqlalchemy.orm import Session

from schemas import schemas
from .models import PIDMREvent


def create_pidmr_event(db: Session, event: schemas.PIDMResolutionEvent):
    db_event = PIDMREvent(time_stamp = event.time_stamp, pid_id = event.pid_id, pid_type = event.pid_type, pid_endpoint = event.pid_endpoint)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
