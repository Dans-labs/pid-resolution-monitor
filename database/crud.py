from typing import Union

from sqlalchemy.orm import Session

from schemas.schemas import User, PIDMResolutionEvent, PIDMResolutionRecord
from utils.auth import verify_password
from .database import get_db
from .models import PIDMREvent, MonitorRecord, Users


def create_pidmr_event(db: Session, event: PIDMResolutionEvent):
    db_event = PIDMREvent(time_stamp=event.time_stamp, pid_id=event.pid_id, pid_mode=event.pid_mode,
                          pid_type=event.pid_type,
                          pid_endpoint=event.pid_endpoint)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def save_pid_resolution_record(record: PIDMResolutionRecord):
    db_record = MonitorRecord(
        time_stamp=record.time_stamp,
        pid_id=record.pid_id,
        pid_url=record.pid_url,
        status_code=record.status_code,
        ssl_verified=record.ssl_verified,
        redirect_count=record.redirect_count,
        resolution_url=record.resolution_url,
        http_error=record.http_error
    )
    db = next(get_db())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def authenticate_user(db: Session, username: str, password: str) -> Union[User, bool]:
    user = db.query(Users).filter(Users.username == username).first()
    if user and verify_password(password, user.password_hash):
        return User(
            username=user.username,
            disabled=user.disabled,
            timestamp=user.time_stamp
        )
    return False


def get_user_by_username(db: Session, username: str) -> Union[User, bool]:
    user = db.query(Users).filter(Users.username == username).first()
    if user:
        return User(
            username=user.username,
            disabled=user.disabled,
            timestamp=user.time_stamp
        )
    return False
