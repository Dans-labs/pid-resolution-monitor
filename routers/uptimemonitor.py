import datetime
import json
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends, Path

from api.uptime_monitor_providers import get_uptimemonitor_provider_obj, get_all_uptimemonitor_instances
from logging_config import prm_logger as logger
from routers.users import get_current_enabled_user
from schemas.schemas import UptimeResponse, User

router = APIRouter(
    prefix="/uptimemonitor",
    tags=["Uptime Monitoring"],
    responses={404: {"description": "Not found"}},
)


# # TODO: Query over different implementations of other uptime monitors; UptimeRobot is the only one implemented so far.
# uptime_robot = UptimeRobot()


@router.get("/providers", response_model=list[dict], summary="List all available uptime monitor providers",
            description="Returns a list of all uptime monitor providers with their name, url, and pid_graph_id.")
def get_uptime_monitor_providers():
    try:
        providers = [
            {
                "name": instance.name,
                "provider_id": instance.pid_graph_id,
                "url": instance.info_url
            }
            for instance in get_all_uptimemonitor_instances()
        ]
        return providers
    except Exception as e:
        logger.error(f"Failed to retrieve uptime monitor providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve uptime monitor providers.")


@router.get("/monitors/{provider_pid}", summary="List all monitors for a specific uptime monitor provider",
            description="Returns a list of all monitors for the specified uptime monitor provider, including their local_id, pid_graph_id, and friendly_name.")
def get_monitors_by_provider(provider_pid: str = Path(..., example="pid_graph:argo",
                                                      description="The provider ID of the uptime monitor."),
                             user: User = Depends(get_current_enabled_user)):
    try:
        uptime_monitor_object = get_uptimemonitor_provider_obj(provider_pid)
        if not uptime_monitor_object:
            raise HTTPException(status_code=404, detail=f"Unknown monitor provider: {provider_pid}")

        # Retrieve monitors
        monitors = uptime_monitor_object.get_all_monitors()
        if not monitors:
            raise HTTPException(status_code=404, detail=f"No monitors found for provider: {provider_pid}")

        # Format response
        response = {
            "responsedate": datetime.datetime.now().strftime("%Y-%m-%d"),
            "provider_pid": provider_pid,
            "provider_name": uptime_monitor_object.name,
            "monitors": [
                {
                    "local_id": mapping.local_id,
                    "pid_graph_id": mapping.pid_graph_id,
                    "friendly_name": mapping.monitor_name
                }
                for mapping in monitors
            ]
        }
        return response
    except Exception as e:
        logger.error(f"Failed to retrieve monitors for provider {provider_pid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve monitors.")


@router.get("/uptime/{provider_pid}/{monitor_pids}", response_model=UptimeResponse,
            summary="Get mean uptime/downtime over the last year for one or more uptime-monitors for a given uptime monitor provider, identified by their pid_graph IDs ('pid_graph:7E709E594').",
            description="The uptime-monitor provider and monitors are identified by their pid_graph IDs. Multiple monitors must be delimited by a hyphen. E.g.: 'pid_graph:15BEDB40-pid_graph:03A715EA-pid_graph:BB4427FE-pid_graph:3E6F3EE6-pid_graph:6AAA1ABD-pid_graph:7E709E594'")
def get_uptime(provider_pid: str, monitor_pids: str, user: Annotated[User, Depends(get_current_enabled_user)]):
    try:
        provider = get_uptimemonitor_provider_obj(provider_pid)
        uptime_data = provider.get_monitors_uptime_by_pidgraph_ids(monitor_pids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not uptime_data:
        raise HTTPException(status_code=404, detail=f"No monitors found for the given PID Graph ID(s): {monitor_pids}")
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
                updates[
                    provider_pgid] = f"re-created {number_updated} monitor mappings from monitor provider: {provider_pgid}."
            else:
                updates[provider_pgid] = "Unknown monitor provider."
                logger.warn(f"Cannot update mmonitor mapping for unknown monitor provider: {provider_pgid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return updates
