import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Path

from api.uptime_monitors import UptimeRobot, get_uptimemonitor_provider_obj
from logging_config import prm_logger as logger
from routers.users import get_current_enabled_user
from schemas.schemas import UptimeResponse, UptimeMonitorsRequest, User

router = APIRouter(
    prefix="/uptimemonitor",
    tags=["Uptime Monitoring"],
    responses={404: {"description": "Not found"}},
)
# TODO: Query over different implementations of other uptime monitors; UptimeRobot is the only one implemented so far.
uptime_robot = UptimeRobot()


def _get_monitor_ids(input_data) -> str:
    # TODO: Query the KnowledgeBase api for the uptime monitors involved.
    return "pid_graph:E2045F7A-pid_graph:456AFBF9-pid_graph:7E94CE2D"


@router.post("/uptime", response_model=UptimeResponse, summary="Get mean uptime over the last passed year.",
             description="The Knowledge Base API provides the related monitor 'stack' that will be queried by: 'Actor', 'Identifier' and 'Institution'")
def get_uptime_by_actor_inst_id(input_data: UptimeMonitorsRequest,
                                user: Annotated[User, Depends(get_current_enabled_user)]):
    pg_monitor_ids = _get_monitor_ids(input_data)
    try:
        uptime_data = uptime_robot.get_monitors_uptime_by_pidgraph_ids(pg_monitor_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return json.loads(uptime_data)


@router.get("/uptime/{pid_graph_ids}", response_model=UptimeResponse,
            summary="Get mean uptime over the last year for one or more uptime-monitors, identified by their pid_graph IDs ('pid_graph:12345678').",
            description="The uptime-monitors are identified by their pid_graph IDs. Multiple monitors must be delimited by a hyphen. E.g.: 'pid_graph:E2045F7A-pid_graph:456AFBF9-pid_graph:7E94CE2D'")
def get_uptime(pid_graph_ids: str, user: Annotated[User, Depends(get_current_enabled_user)]):
    try:
        uptime_data = uptime_robot.get_monitors_uptime_by_pidgraph_ids(pid_graph_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return json.loads(uptime_data)


@router.put("/update{pid_graph_ids}", status_code=201,
            summary="Updates the pid_graph-to-monitor mappings.",
            description="For each monitor provider, it maps pid_graph monitor IDs (pid_graph:E2045F7A) to their associated local monitor IDs (797637034). Multiple monitors providers must be delimited by a hyphen. E.g.: 'pid_graph:E2045F7A-pid_graph:456AFBF9'",
            dependencies=[Depends(get_current_enabled_user)], response_model=dict)
def update_uptime_monitors(pid_graph_ids: str = Path(..., example="pid_graph:uptimerobot",
                                                     description="pid_graph_id of the Uptime Monitor Provider."),
                           user: User = Depends(get_current_enabled_user)):
    try:
        updates = {}
        for provider_pgid in pid_graph_ids.split('-'):
            uptime_monitor_object = get_uptimemonitor_provider_obj(provider_pgid)
            if uptime_monitor_object:
                number_updated = uptime_monitor_object.update_monitors_mapping(force_update=True)
                updates[provider_pgid] = f"re-created {number_updated} mappings."
            else:
                updates[provider_pgid] = "Unknown monitor provider."
                logger.warn(f"Cannot update mmonitor mapping for unknown monitor provider: {provider_pgid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return updates
