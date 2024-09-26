import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends

from api.uptimerobot import UptimeRobot
from routers.users import get_current_enabled_user
from schemas.schemas import UptimeResponse, UptimeMonitorsRequest, User

router = APIRouter(
    prefix="/uptimemonitor",
    tags=["Uptime Monitoring"],
    responses={404: {"description": "Not found"}},
)

uptime_robot = UptimeRobot()


def _get_monitor_ids(input_data) -> str:
    # TODO: Query the KB api for the uptime monitors involved.
    return "pid_graph:E2045F7A-pid_graph:456AFBF9-pid_graph:7E94CE2D"


@router.post("/uptime", response_model=UptimeResponse, summary="Get mean uptime over the last passed year.",
             description="The Knowledge Base API provides the related monitor 'stack' that will be queried by: 'Actor', 'Identifier' and 'Institution'")
def get_uptime_by_actor_inst_id(input_data: UptimeMonitorsRequest,
                                user: Annotated[User, Depends(get_current_enabled_user)]):
    related_monitors = _get_monitor_ids(input_data)
    try:
        uptime_data = uptime_robot.get_monitors_uptime_by_pidgraph_ids(related_monitors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return json.loads(uptime_data)


@router.get("/uptime/{pidgraph_ids}", response_model=UptimeResponse,
            summary="Get mean uptime over the last year, for a list of Uptime Monitor ID's ('pid_graph:12345678')",
            description="The Uptime Monitors are identified by their PID Graph IDs. Multiple monitors must be separated by a hyphen. E.g.: 'pid_graph:E2045F7A-pid_graph:456AFBF9-pid_graph:7E94CE2D'")
def get_uptime(pidgraph_ids: str, user: Annotated[User, Depends(get_current_enabled_user)]):
    try:
        uptime_data = uptime_robot.get_monitors_uptime_by_pidgraph_ids(pidgraph_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return json.loads(uptime_data)


@router.put("/uptimerobot/update", status_code=201,
            summary="Re-creates pid_graph identifier to UptimeRobot identifier mapping.",
            description="i.e: PID Graph ID (pid_graph:E2045F7A) -> UptimeRobot Monitor ID (797637034).",
            dependencies=[Depends(get_current_enabled_user)])
def update_uptime_monitors():
    try:
        number_updated = uptime_robot.update_monitors_mapping()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": f"Successfully re-created {number_updated} UptimeRobot monitor identifier mappings."}
