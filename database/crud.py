from datetime import datetime, timedelta
from typing import Union, List

from sqlalchemy import and_, distinct
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api.pidresolver import ResolutionRecord
from logging_config import prm_logger as logger
from schemas.schemas import User, PidMrEventRecord, PidResolutionCreateBatch, PidResolutionUpdateBatch, \
    UptimemonitorMapping, PidBaseBatch
from settings import settings
from utils.auth import verify_password
from .database import get_db
from .models import PIDMREvent, MonitorRecord, Users, PIDResolutionBatches, PIDS, UptimemonitorsMapping, PIDMRResolution


def create_pidmr_event(event: PidMrEventRecord, db: Session) -> PIDMREvent:
    db_event = PIDMREvent(time_stamp=event.time_stamp, pid_id=event.pid_id, pid_mode=event.pid_mode,
                          pid_type=event.pid_type,
                          pid_endpoint=event.pid_endpoint, pid_resolver_status=event.pid_resolver_status)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def save_pid_resolution_results(record: ResolutionRecord, batch_id: int, pid_type: str) -> MonitorRecord:
    db_record = MonitorRecord(
        batch_id=batch_id,
        time_stamp=record.time_stamp,
        pid_id=record.pid_id,
        pid_url=record.pid_url,
        pid_type=pid_type,
        status_code=record.status_code,
        content_type=record.content_type,
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


def add_pidmr_resolution_event(pidmr_event_id: int, pid_resolution_id: int) -> None:
    db_record = PIDMRResolution(
        resolution_id=pid_resolution_id,
        pidmr_event_id=pidmr_event_id
    )
    db = next(get_db())
    db.add(db_record)
    db.commit()


def insert_pid_resolution_batch(sample: PidResolutionCreateBatch, username: str, db: Session) -> int:
    # Create a new PIDResolutionSample record
    new_sample_batch = PIDResolutionBatches(
        actor=sample.actor,
        institution=sample.institution,
        description=sample.description,
        user=username
    )
    db.add(new_sample_batch)
    db.commit()
    db.refresh(new_sample_batch)  # Gets the auto-inc generated batchID
    logger.debug(f"Creating new PID resolution batch. Batch_id: '{new_sample_batch.id}', for user: {username}")
    # Insert sample_pids into the PIDS table
    for pid in sample.sample_pids:
        logger.info(f"Adding PID to batch: {pid}")
        new_pid = PIDS(
            batch_id=new_sample_batch.id,
            pid_id=pid,
            pid_type=sample.identifier_type
        )
        db.add(new_pid)
    db.commit()
    return new_sample_batch.id


def get_pid_resolution_batch(batch_id: int, db: Session) -> Union[PidBaseBatch, bool]:
    batch = db.query(PIDResolutionBatches).filter(PIDResolutionBatches.id == batch_id).first()
    if batch:
        total_pids = get_total_pids_by_batch(batch_id, db)
        identifiertype = None  # use None if not available, or if multiple types are found.
        distinct_identifiertypes = db.query(distinct(PIDS.pid_type)).filter(
            PIDS.batch_id == batch_id
        ).all()
        if len(distinct_identifiertypes) == 1:
            identifiertype = distinct_identifiertypes[0][0]
        return PidBaseBatch(
            batch_id=batch.id,
            total_pids=total_pids,
            identifier_type=identifiertype,
            actor=batch.actor,
            institution=batch.institution,
            description=batch.description
        )
    return False


def get_pidslist_for_batch(batch_id, limit, offset, db) -> List[str]:
    pids = db.query(PIDS.pid_id).filter(PIDS.batch_id == batch_id).offset(offset).limit(limit).all()
    return [pid[0] for pid in pids]


def get_total_pids_by_batch(batch_id, db) -> int:
    return db.query(PIDS).filter(PIDS.batch_id == batch_id).count()


def update_pid_resolution_batch(update_batch: PidResolutionUpdateBatch, db: Session) -> Union[List[str], bool]:
    # Find batch to update by provided id, actor and institution:
    existing_batch = db.query(PIDResolutionBatches).filter(
        PIDResolutionBatches.id == update_batch.id,
        PIDResolutionBatches.actor == update_batch.actor,
        PIDResolutionBatches.institution == update_batch.institution
    ).first()

    if not existing_batch:
        return False

    distinct_identifiertypes = db.query(distinct(PIDS.pid_type)).filter(
        PIDS.batch_id == existing_batch.id
    ).all()

    # Identifier type must be the same for all PIDs in the batch. Beware: cannot be used for the PIDMR batch.
    if len(distinct_identifiertypes) != 1 or update_batch.identifier_type != distinct_identifiertypes[0][0]:
        return False

    existing_pids = db.query(PIDS.pid_id).filter(
        PIDS.batch_id == existing_batch.id,
        PIDS.pid_type == update_batch.identifier_type
    ).all()
    existing_pids_set = {pid[0] for pid in existing_pids}

    # Add new PIDs to the batch that are not already in the batch:
    added_pids = []
    for pid in update_batch.sample_pids:
        if pid not in existing_pids_set:  # TODO: take different formats of the same PID into account.
            new_pid = PIDS(
                batch_id=update_batch.id,
                pid_id=pid,
                pid_type=update_batch.identifier_type
            )
            db.add(new_pid)
            added_pids.append(pid)

    db.commit()
    return added_pids


def get_pid_resolution_percentage_by_batch_id(batch_id: int, db: Session) -> dict:
    total_pids = db.query(MonitorRecord).filter(MonitorRecord.batch_id == batch_id).count()
    resolved_pids = db.query(MonitorRecord).filter(MonitorRecord.batch_id == batch_id, MonitorRecord.status_code == 200).count()
    if total_pids == 0:
        return {"resolution_percentage": 0.0, "total_pids": total_pids}
    return {"resolution_percentage": round((resolved_pids / total_pids) * 100, 1), "total_pids": total_pids}
# return {"resolution_percentage": f"{round((resolved_pids / total_pids) * 100, 1):.1f}", "total_pids": total_pids}


def update_uptimemonitor_mapping(mapping: List[UptimemonitorMapping], provider_pgid: str) -> int:
    db = next(get_db())
    for map in mapping:
        upsert_stmt = insert(UptimemonitorsMapping).values(
            monitor_pgid=map.pid_graph_id,
            monitor_id=map.local_id,
            monitor_name=map.monitor_name,
            provider_pgid=provider_pgid,
            last_updated=datetime.now()
        ).on_conflict_do_update(
            index_elements=['monitor_pgid'],
            set_={
                'monitor_id': map.local_id,
                'monitor_name': map.monitor_name,
                'provider_pgid': provider_pgid,
                'last_updated': datetime.now()
            }
        )
        db.execute(upsert_stmt)
    db.commit()
    return len(mapping)


def check_uptimemonitor_mapping_needs_update(provider_pgid: str) -> bool:
    # Check to see if there are any records at all for this provider:
    db = next(get_db())
    result = db.query(UptimemonitorsMapping).filter(UptimemonitorsMapping.provider_pgid == provider_pgid).first()
    if not result:
        return True
    hours_ago = datetime.now() - timedelta(hours=settings.UPTIMEMONITOR_MAX_STALE_HOURS)
    result = db.query(UptimemonitorsMapping).filter(
        and_(
            UptimemonitorsMapping.last_updated < hours_ago,
            UptimemonitorsMapping.provider_pgid == provider_pgid
        )).first()
    return result is not None


def create_magic_pidmr_pidbatch() -> bool:
    # Check to see if the magic PIDMR batch with id=1 already exists. If not, create it.
    db = next(get_db())
    bln_success = False
    pidmr_batch = PIDResolutionBatches(
        id=1,
        actor="pid_graph:pidmr",
        institution="pid_graph:pidmr",
        description="Dedicated PIDMR batch number 1.",
        user="pidmr"
    )
    try:
        db.add(pidmr_batch)
        db.commit()
        bln_success = True
        logger.info("Dedicated PIDMR batch number 1 CREATED.")
    except Exception as e:
        logger.info("Dedicated PIDMR batch number 1 EXISTS.")

    return bln_success


def get_monitor_ids_by_pgid_list(pgid_list: List[str]) -> List[str]:
    db = next(get_db())
    result = db.query(UptimemonitorsMapping.monitor_id).filter(
        UptimemonitorsMapping.monitor_pgid.in_(pgid_list)
    ).all()
    return [row.monitor_id for row in result]


def authenticate_user(username: str, password: str, db: Session) -> Union[User, bool]:
    user = db.query(Users).filter(Users.username == username).first()
    if user and verify_password(password, user.password_hash):
        return User(
            username=user.username,
            disabled=user.disabled,
            time_stamp=user.time_stamp
        )
    return False


def get_user_by_username(username: str, db: Session) -> Union[User, bool]:
    user = db.query(Users).filter(Users.username == username).first()
    if user:
        return User(
            username=user.username,
            disabled=user.disabled,
            time_stamp=user.time_stamp
        )
    return False
