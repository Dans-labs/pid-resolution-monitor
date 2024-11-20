from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey, Sequence

from .database import Base


class MonitorRecord(Base):
    __tablename__ = "pid_resolution"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('pid_batches.id'), nullable=False)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)
    pid_id = Column(String, nullable=False)  # pid in any form
    pid_url = Column(String, nullable=False)  # actionable url of the pid
    pid_type = Column(String,
                      nullable=True)  # Type PID, ie. doi, handle, etc. represented as: pid_graph ID (pid_graph:3E6F3EE6)
    status_code = Column(Integer, nullable=True)  # status codes or unresolved
    content_type = Column(String, nullable=True)  # Content-Type from header, if resolved
    ssl_verified = Column(Boolean, nullable=False)  # True or False
    redirect_count = Column(Integer, nullable=True)  # number of redirects
    resolution_url = Column(String, nullable=True)  # resolved url
    http_error = Column(String, nullable=True)  # error message


class PIDMREvent(Base):
    __tablename__ = "pidmr_events"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)  # time of the PIDMR event
    pid_id = Column(String, nullable=False)
    pid_mode = Column(String, nullable=False)  # Either: landingpage, metadata or resource
    pid_type = Column(String, nullable=True)
    pid_endpoint = Column(String, nullable=False)
    pid_resolver_status = Column(Integer, nullable=True)


class Users(Base):
    __tablename__ = "prm_users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    disabled = Column(Boolean, nullable=False)
    time_stamp = Column(DateTime, nullable=False, default=datetime.now)


class PIDResolutionBatches(Base):
    __tablename__ = "pid_batches"
    id = Column(Integer, Sequence('pid_batches_id_seq', start=2), primary_key=True)
    actor = Column(String, nullable=False)
    institution = Column(String, nullable=False)
    description = Column(String, nullable=True)
    user = Column(String, nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.now)
    __table_args__ = (UniqueConstraint('actor', 'institution', name='uq_actor_institution'),)


class PIDS(Base):
    __tablename__ = "pids"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('pid_batches.id'), nullable=False)
    pid_id = Column(String, nullable=False)  # pid 'value'/string as submitted
    pid_type = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint('batch_id', 'pid_id', name='uq_batch_pid_id'),)


class PIDMRResolution(Base):
    __tablename__ = "pidmr_resolution"
    resolution_id = Column(Integer, ForeignKey('pid_resolution.id'), primary_key=True, nullable=False)
    pidmr_event_id = Column(Integer, ForeignKey('pidmr_events.id'), primary_key=True, nullable=False)


class UptimemonitorsMapping(Base):
    __tablename__ = "uptimemonitors_mapping"
    monitor_pgid = Column(String, primary_key=True)
    monitor_id = Column(String, nullable=False)
    monitor_name = Column(String, nullable=False)
    provider_pgid = Column(String, nullable=False)  # provider pid_graph id. ie. pid_graph:3E6F3EE6 for UptimeRobot.
    last_updated = Column(DateTime, nullable=False, default=datetime.now)
