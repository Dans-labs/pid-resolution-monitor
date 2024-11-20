import datetime
import json
import os
from abc import abstractmethod, ABC
from typing import List, Union

import httpx
from dateutil.relativedelta import relativedelta

from database.crud import update_uptimemonitor_mapping, check_uptimemonitor_mapping_needs_update, \
    get_monitor_ids_by_pgid_list
from logging_config import prm_logger as logger
from schemas.schemas import UptimemonitorMapping
from settings import settings


def get_uptimemonitor_provider_obj(pid_graph_id: str):
    if pid_graph_id == "pid_graph:uptimerobot":
        return UptimeRobot()
    return None


class UptimeMonitor(ABC):
    def __init__(self):
        self.name = "UptimeMonitor"
        self.pid_graph_id = "pid_graph:uptimemonitor"
        self.uptimemonitor_api_key = 'UPTIMEMONITOR_API_KEY'

    @abstractmethod
    def update_monitors_mapping(self, force_update: bool = False) -> Union[int, bool]:
        pass


class UptimeRobot(UptimeMonitor):

    def __init__(self):
        self.name = "UptimeRobot"
        self.pid_graph_id = "pid_graph:uptimerobot"
        self.uptimemonitor_api_key = os.getenv('UPTIMEROBOT_API_KEY')

    def update_monitors_mapping(self, force_update: bool = False) -> Union[int, bool]:
        if force_update or check_uptimemonitor_mapping_needs_update(
                self.pid_graph_id):  # Short-circuit evaluation: Skip the check, if force-update is True...
            return self._update_monitors_mapping()
        return False

    def _update_monitors_mapping(self) -> int:
        """
        Updates the UptimeRobot monitors mapping in the database.
        Raises:
            Exception: If an HTTP error with the Monitors API occurs.
        """

        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Content-Type": "application/x-www-form-urlencoded"})
        limit = 50
        new_results = True
        offset = 0
        while new_results:
            payload = f'api_key={self.uptimemonitor_api_key}&format=json&logs=0&offset={offset}&limit={limit}'
            logger.debug(payload)
            try:
                response = httpx_client.post(settings.UPTIMEROBOT_ENDPOINT, data=payload)
                data = response.json()
            except Exception as e:
                logger.warn(f"Updating UptimeRobot monitors mapping failed: {e}")
                raise Exception(
                    f"Updating UptimeRobot mappings failed! Check if uptime monitor endpoint ({settings.UPTIMEROBOT_ENDPOINT}) is reachable and try again.")
            if data["stat"] == "fail":
                raise Exception(data["error"]["message"])
            total = data['pagination']['total']
            mappings = []
            for monitor in data['monitors']:
                monitor_id = monitor['id']
                friendly_name_field = monitor['friendly_name'].split(';', 1)
                pid_graph_id = friendly_name_field[1].strip()
                logger.debug(pid_graph_id + " (" + friendly_name_field[0].strip() + ") " + str(monitor_id))
                mappings.append(UptimemonitorMapping(pid_graph_id, str(monitor_id), friendly_name_field[0].strip()))
            offset += limit
            new_results = total > offset
            httpx_client.close()
            logger.info(f"{self.name} monitor ({self.pid_graph_id}) mappings updated. Total monitors: {total}")
            update_uptimemonitor_mapping(mappings, self.pid_graph_id)
            for mapping in mappings:
                logger.info(f'"{mapping.pid_graph_id}": "{mapping.local_id}"')
        return total

    def get_monitors_uptime_by_pidgraph_ids(self, pidgraph_ids: str) -> str:
        monitor_ids = get_monitor_ids_by_pgid_list(pidgraph_ids.split('-'))
        return self.get_monitors_mean_uptime(monitor_ids)

    def get_monitors_mean_uptime(self, monitor_ids: List[str]) -> str:
        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Content-Type": "application/x-www-form-urlencoded"})

        now = datetime.datetime.now()
        oneyearago = now - relativedelta(years=1)
        days_in_last_year = (now - oneyearago).days

        time_range = f'{int(oneyearago.timestamp())}_{int(now.timestamp())}'
        payload = f'api_key={self.uptimemonitor_api_key}&format=json&logs=0&monitors={"-".join(monitor_ids)}&custom_uptime_ranges={time_range}'
        logger.debug(payload)
        response = httpx_client.post(settings.UPTIMEROBOT_ENDPOINT, data=payload)
        data = response.json()
        httpx_client.close()

        if data["stat"] == "fail":
            raise Exception(data["error"]["message"])

        uptime_ranges = [float(monitor['custom_uptime_ranges']) for monitor in data['monitors']]
        mean_uptime = sum(uptime_ranges) / len(uptime_ranges)
        downtime_days = (1 - (mean_uptime / 100)) * days_in_last_year

        # Create response JSON:
        transformed_monitors = []
        for monitor in data['monitors']:
            friendly_name_field = monitor['friendly_name'].split(';', 1)
            transformed_monitor = {
                "id": monitor["id"],
                "pid_graph_id": friendly_name_field[1].strip(),
                "friendly_name": friendly_name_field[0].strip(),
                "url": monitor["url"],
                "uptime": monitor["custom_uptime_ranges"]
            }
            transformed_monitors.append(transformed_monitor)
        transformed_data = {
            "stat": data["stat"],
            "mean_uptime": round(mean_uptime, 3),
            "days_downtime": round(downtime_days, 4),
            "timestamp_interval": time_range,
            "monitors": transformed_monitors
        }
        return json.dumps(transformed_data, indent=4)


if __name__ == "__main__":
    uptimerobo = get_uptimemonitor_provider_obj("pid_graph:uptimerobot")
    if uptimerobo:
        result = uptimerobo.update_monitors_mapping(force_update=True)
