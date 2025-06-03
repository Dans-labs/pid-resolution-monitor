import datetime
import json
import os
from abc import ABC
from typing import List, Union

import httpx
import jmespath
from dateutil.relativedelta import relativedelta

from database.crud import update_uptimemonitor_mapping, check_uptimemonitor_mapping_needs_update, \
    get_monitor_ids_by_pgid_list
from logging_config import prm_logger as logger
from schemas.schemas import UptimemonitorMapping
from settings import settings


def get_uptimemonitor_provider_obj(pid_graph_id: str):
    for instance in get_all_uptimemonitor_instances():
        if instance.pid_graph_id == pid_graph_id:
            return instance
    return None


def get_all_uptimemonitor_instances() -> list:
    """
    Returns a list of all instantiated UptimeMonitor providers.
    """
    return [Argo(), UptimeRobot()]

def update_all_monitor_providers_mapping(force_update: bool = False) -> None:
    for instance in get_all_uptimemonitor_instances():
        instance.update_monitors_mapping(force_update=force_update)


class UptimeMonitor(ABC):
    def __init__(self):
        self.name = NotImplemented
        self.pid_graph_id = NotImplemented
        self.uptimemonitor_api_key = NotImplemented
        self.info_url = NotImplemented

    def update_monitors_mapping(self, force_update: bool = False) -> Union[int, bool]:
        if force_update or check_uptimemonitor_mapping_needs_update(self.pid_graph_id):  # Short-circuit evaluation: Skip the check, if force-update is True...
            return self._update_monitors_mapping()
        return False

    def get_monitors_uptime_by_pidgraph_ids(self, pidgraph_ids: str) -> str:
        pass

    def get_monitors_mean_uptime(self, monitor_ids: List[str]) -> str:
        pass

    def get_all_monitors(self) -> list[UptimemonitorMapping]:
        pass


class UptimeRobot(UptimeMonitor):

    def __init__(self):
        self.name = "UptimeRobot"
        self.pid_graph_id = "pid_graph:uptimerobot"
        self.uptimemonitor_api_key = os.getenv('UPTIMEROBOT_API_KEY')
        self.info_url = settings.UPTIMEROBOT_API


    def get_all_monitors(self) -> list[UptimemonitorMapping]:
        """
        Retrieves all monitors from UptimeRobot and returns them as a JSON string.
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
                logger.warn(f"Updating {self.name}  monitors mapping failed: {e}")
                raise Exception(
                    f"Updating {self.name}  mappings failed! Check if uptime monitor endpoint ({settings.UPTIMEROBOT_ENDPOINT}) is reachable and try again.")
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
            logger.info(f"{self.name} monitor ({self.pid_graph_id}). Total monitors: {total}")

            for mapping in mappings:
                logger.info(f'"{mapping.monitor_name}" => "{mapping.pid_graph_id}" <=> "{mapping.local_id}"')

        return mappings

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
                logger.warn(f"Updating {self.name}  monitors mapping failed: {e}")
                raise Exception(
                    f"Updating {self.name}  mappings failed! Check if uptime monitor endpoint ({settings.UPTIMEROBOT_ENDPOINT}) is reachable and try again.")
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
                logger.info(f'"{mapping.monitor_name}" => "{mapping.pid_graph_id}" <=> "{mapping.local_id}"')
        return total

# TODO: Check: monitor_ids blijken local_ids, geen pid_graph:ids, zoals bij AGRO monitor....

    def get_monitors_uptime_by_pidgraph_ids(self, pidgraph_ids: str) -> str:
        monitor_ids = get_monitor_ids_by_pgid_list(pidgraph_ids.split('-'), self.pid_graph_id) # Gets mapping from DB
        # print(f"Monitor IDs: {monitor_ids}") #Monitor IDs: [('797637034', 'pid_graph:03A715EA'), ('797636982', 'pid_graph:15BEDB40')]
        return self.get_monitors_mean_uptime([item[0] for item in monitor_ids])


    def get_monitors_mean_uptime(self, monitor_local_ids: List[str]) -> str:

        if not monitor_local_ids:
            return
        # else: # Get the monitor local_id <=> pid_graph:id mapping from the database:
        #     monitor_ids_mapping = get_monitor_ids_by_pgid_list(monitor_local_ids, self.pid_graph_id)

        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Content-Type": "application/x-www-form-urlencoded"})
        now = datetime.datetime.now()
        oneyearago = now - relativedelta(years=1)
        days_in_last_year = (now - oneyearago).days

        time_range = f'{int(oneyearago.timestamp())}_{int(now.timestamp())}'
        payload = f'api_key={self.uptimemonitor_api_key}&format=json&logs=0&monitors={"-".join(monitor_local_ids)}&custom_uptime_ranges={time_range}' #[item[0] for item in monitor_ids_mapping]
        logger.info(payload)
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
                "id": str(monitor["id"]),
                "pid_graph_id": friendly_name_field[1].strip(),
                "friendly_name": friendly_name_field[0].strip(),
                "url": monitor["url"],
                "uptime": monitor["custom_uptime_ranges"]
            }
            transformed_monitors.append(transformed_monitor)
        transformed_data = {
            "stat": data["stat"],
            "provider_name": self.name,
            "mean_uptime": round(mean_uptime, 3),
            "days_downtime": round(downtime_days, 4),
            "hours_downtime": round(downtime_days * 24, 3),
            "timestamp_interval": time_range,
            "monitors": transformed_monitors
        }
        return json.dumps(transformed_data, indent=4)


class Argo(UptimeMonitor):

    def __init__(self):
        self.name = "ARGO"
        self.pid_graph_id = "pid_graph:argo"
        self.uptimemonitor_api_key = os.getenv('ARGO_API_KEY')  # x-api-key
        self.info_url = settings.AGRO_API

    def get_all_monitors(self) -> list[UptimemonitorMapping]:
        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Accept": "application/json", "x-api-key": self.uptimemonitor_api_key})
        new_results = True
        while new_results:
            try:
                response = httpx_client.get(settings.AGRO_ENDPOINT)
                data = response.json()
            except Exception as e:
                logger.warn(f"Updating {self.name} monitors mapping failed: {e}")
                raise Exception(
                    f"Updating {self.name}  mappings failed! Check if uptime monitor endpoint ({settings.AGRO_ENDPOINT}) is reachable and try again.")
            if data["status"]["code"] != "200":
                raise Exception(data["status"]["message"])

            total = 0  # TODO: Check if/how pagination works in ARGO
            mappings = []
            for monitor in data['data']:
                if not monitor['tags'].get('info_ID', 'default').startswith("pid_graph:"):
                    # Skip monitors that do not have a pid_graph ID in the 'tags'
                    continue
                monitor_id = monitor[
                    'hostname']  # Use hostname. Looks a concatenation of tags.hostname and tags.info_ID. Not sure what the internal identifier is.
                friendly_name = monitor['group']
                pid_graph_id = monitor['tags']['info_ID']
                logger.debug(pid_graph_id + " (" + friendly_name.strip() + ") " + str(monitor_id))
                mappings.append(UptimemonitorMapping(pid_graph_id, friendly_name.strip(), friendly_name.strip()))
                total = total + 1

            new_results = False
            httpx_client.close()
            logger.info(f"{self.name} monitor ({self.pid_graph_id}) mappings updated. Total monitors: {total}")

            for mapping in mappings:
                logger.info(f'"{mapping.monitor_name}" => "{mapping.pid_graph_id}" <=> "{mapping.local_id}"')
        return mappings

    def _update_monitors_mapping(self) -> bool:
        """
        Updates the ARGO monitors mapping in the database.
        Raises:
            Exception: If an HTTP error with the Monitors API occurs.
        """

        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Accept": "application/json", "x-api-key": self.uptimemonitor_api_key})
        new_results = True
        while new_results:
            try:
                response = httpx_client.get(settings.AGRO_ENDPOINT)
                data = response.json()
            except Exception as e:
                logger.warn(f"Updating {self.name} monitors mapping failed: {e}")
                raise Exception(
                    f"Updating {self.name}  mappings failed! Check if uptime monitor endpoint ({settings.AGRO_ENDPOINT}) is reachable and try again.")
            if data["status"]["code"] != "200":
                raise Exception(data["status"]["message"])

            total = 0  # TODO: Check if/how pagination works in ARGO
            mappings = []
            for monitor in data['data']:
                if not monitor['tags'].get('info_ID', 'default').startswith("pid_graph:"):
                    # Skip monitors that do not have a pid_graph ID in the 'tags'
                    continue
                monitor_id = monitor[
                    'hostname']  # Use hostname. Looks a concatenation of tags.hostname and tags.info_ID. Not sure what the internal identifier is.
                friendly_name = monitor['group']
                pid_graph_id = monitor['tags']['info_ID']
                logger.debug(pid_graph_id + " (" + friendly_name.strip() + ") " + str(monitor_id))
                mappings.append(UptimemonitorMapping(pid_graph_id, friendly_name.strip(), friendly_name.strip()))
                total = total + 1

            new_results = False
            httpx_client.close()
            logger.info(f"{self.name} monitor ({self.pid_graph_id}) mappings updated. Total monitors: {total}")
            update_uptimemonitor_mapping(mappings, self.pid_graph_id)
            for mapping in mappings:
                logger.info(f'"{mapping.monitor_name}" => "{mapping.pid_graph_id}" <=> "{mapping.local_id}"')
        return total


    def get_monitors_uptime_by_pidgraph_ids(self, pidgraph_ids: str) -> str:
        return self.get_monitors_mean_uptime(pidgraph_ids.split('-'))

    # TODO: Input param 'monitor_pgids' should be a list of local IDs, not pid_graph IDs.
    def get_monitors_mean_uptime(self, monitor_pgids: List[str]) -> str:

        if not monitor_pgids:
            return

        monitor_props = {}
        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Accept": "application/json", "x-api-key": self.uptimemonitor_api_key})
        try:
            response = httpx_client.get(settings.AGRO_ENDPOINT)
            data = response.json()

            for pgid_monitor in data['data']:
                if not pgid_monitor['tags'].get('info_ID', 'default').startswith("pid_graph:"):
                    # Skip monitors that do not have a pid_graph ID in the 'tags'
                    continue
                monitor_props[pgid_monitor['tags']['info_ID']] = (pgid_monitor['group'], pgid_monitor['tags']['info_URL'])

            httpx_client.close()

        except Exception as e:
            logger.warn(f"Updating {self.name} monitors mapping failed: {e}")
            raise Exception(
                f"Updating {self.name}  mappings failed! Check if uptime monitor endpoint ({settings.AGRO_ENDPOINT}) is reachable and try again.")
        if data["status"]["code"] != "200":
            raise Exception(data["status"]["message"])

        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Accept": "application/json",
                                             "x-api-key": self.uptimemonitor_api_key}
                                    )
        # https://api.devel.mon.argo.grnet.gr/api/v2/results/CORE/SERVICEGROUPS/ROR?start_time=2025-05-01T00:00:00Z&end_time=2026-05-01T00:00:00Z&granularity=monthly
        now = datetime.datetime.now()
        oneyearago = now - relativedelta(years=1)
        days_in_last_year = (now - oneyearago).days
        report_name= "CORE"
        endpoint_group_type = "SERVICEGROUPS"

        time_range = f'{int(oneyearago.timestamp())}_{int(now.timestamp())}'

        argo_url = f'https://api.devel.mon.argo.grnet.gr/api/v2/results/{report_name}/{endpoint_group_type}?start_time={oneyearago.strftime('%Y-%m-%dT%H:%M:%SZ')}&end_time={now.strftime('%Y-%m-%dT%H:%M:%SZ')}&granularity=monthly'

        logger.info(argo_url)

        response = httpx_client.get(argo_url)
        status_code = response.status_code
        data = response.json()
        httpx_client.close()

        if data.get("results", "empty") == "empty" or status_code != 200:
            raise Exception(data["errors"][0]["details"])

        transformed_monitors = []
        _overall_uptime = 0
        for pgid_monitor in monitor_pgids:
            mon_name = monitor_props.get(pgid_monitor, ("", ""))[0]
            ark_results = jmespath.search(f"results[].endpoints[?name=='{mon_name}'].results[]", data)
            if not ark_results:
                logger.warning(f"No ARGO results found for monitor: {mon_name} ({pgid_monitor})")
                continue
            uptime = 0
            for result in ark_results[0]:
                uptime = uptime + float(result['uptime'])
            mean_uptime = uptime / len(ark_results[0])

            transformed_monitor = {
                "id": str(mon_name),
                "pid_graph_id": pgid_monitor,
                "friendly_name": mon_name,
                "url": monitor_props.get(pgid_monitor, ("", ""))[1],
                "uptime": str(round(mean_uptime, 4))
            }

            transformed_monitors.append(transformed_monitor)
            _overall_uptime = _overall_uptime + mean_uptime

        mean_overall_uptime = _overall_uptime / len(monitor_pgids)
        downtime_days = (1 - mean_overall_uptime) * days_in_last_year
        transformed_data = {
            "stat": "ok",
            "provider_name": self.name,
            "mean_uptime": round(mean_overall_uptime, 3),
            "days_downtime": round(downtime_days, 4),
            "hours_downtime": round(downtime_days * 24, 3),
            "timestamp_interval": time_range,
            "monitors": transformed_monitors
        }
        return json.dumps(transformed_data, indent=4)
