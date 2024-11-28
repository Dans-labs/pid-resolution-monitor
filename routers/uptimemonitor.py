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


@router.get("/uptime/{pid_graph_ids}", response_model=UptimeResponse,
            summary="Get mean uptime/downtime over the last year for one or more uptime-monitors, identified by their pid_graph IDs ('pid_graph:7E709E594').",
            description="The uptime-monitors are identified by their pid_graph IDs. Multiple monitors must be delimited by a hyphen. E.g.: 'pid_graph:15BEDB40-pid_graph:03A715EA-pid_graph:BB4427FE-pid_graph:3E6F3EE6-pid_graph:6AAA1ABD-pid_graph:7E709E594'")
def get_uptime(pid_graph_ids: str, user: Annotated[User, Depends(get_current_enabled_user)]):
    try:
        uptime_data = uptime_robot.get_monitors_uptime_by_pidgraph_ids(pid_graph_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not uptime_data:
        raise HTTPException(status_code=404, detail=f"No monitors found for the given PID Graph ID(s): {pid_graph_ids}")
    return json.loads(uptime_data)


@router.put("/update/{pid_graph_ids}", status_code=201,
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
                updates[provider_pgid] = f"re-created {number_updated} monitor mappings from monitor provider: {provider_pgid}."
            else:
                updates[provider_pgid] = "Unknown monitor provider."
                logger.warn(f"Cannot update mmonitor mapping for unknown monitor provider: {provider_pgid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return updates
