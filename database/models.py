from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean

from .database import Base


class MonitorRecord(Base):
    __tablename__ = "pid_resolution"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)
    pid_id = Column(String, nullable=False)  # pid of the record
    pid_url = Column(String, nullable=False)  # actionable url of the pid
    status_code = Column(Integer, nullable=True)  # status codes or unresolved
    ssl_verified = Column(Boolean, nullable=False)  # True or False
    redirect_count = Column(Integer, nullable=True)  # number of redirects
    resolution_url = Column(String, nullable=True)  # resolved url
    http_error = Column(String, nullable=True)  # error message


class PIDMREvent(Base):
    __tablename__ = "pidmr_events"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)
    pid_id = Column(String, nullable=False)
    pid_mode = Column(String, nullable=False)
    pid_type = Column(String, nullable=True)
    pid_endpoint = Column(String, nullable=False)
