from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from .database import Base


class MonitorRecord(Base):
    __tablename__ = "monitor_record"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)
    status_code = Column(String, nullable=False)
    redirect_count = Column(Integer, nullable=True)
    pid_url = Column(String, nullable=False)


class PIDMREvent(Base):
    __tablename__ = "pidmr_events"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)
    pid_id = Column(String, nullable=False)
    pid_type = Column(String, nullable=False)
    pid_endpoint = Column(String, nullable=False)
