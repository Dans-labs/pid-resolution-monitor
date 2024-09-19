import datetime
import dbm
import json
import os
from typing import List

import httpx
from dateutil.relativedelta import relativedelta

from logging_config import prm_logger as logger
from settings import settings


class UptimeRobot:

    uptimerobot_api_key = os.getenv('UPTIMEROBOT_API_KEY')

    def update_monitors_mapping(self) -> int:
        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Content-Type": "application/x-www-form-urlencoded"})

        limit = 50
        new_results = True
        offset = 0

        with dbm.open(settings.uptime_monitors_mapping_db, 'c') as db:
            while new_results:
                payload = f'api_key={self.uptimerobot_api_key}&format=json&logs=0&offset={offset}&limit={limit}'
                logger.debug(payload)
                response = httpx_client.post('https://api.uptimerobot.com/v2/getMonitors', data=payload)
                data = response.json()
                if data["stat"] == "fail":
                    raise Exception(data["error"]["message"])
                total = data['pagination']['total']
                for monitor in data['monitors']:
                    monitor_id = monitor['id']
                    friendly_name_field = monitor['friendly_name'].split(';', 1)
                    pid_graph_id = friendly_name_field[1].strip()
                    logger.debug(pid_graph_id + " (" + friendly_name_field[0].strip() + ") " + str(monitor_id))
                    db[pid_graph_id] = str(monitor_id)
                offset += limit
                new_results = total > offset
            httpx_client.close()
            logger.info(f"UptimeRobot monitors mapping updated. Total monitors: {total}")
            for k in db.keys():
                logger.info(f'"{k.decode('utf-8')}" :  "{db[k].decode('utf-8')}"')
        return total

    def get_monitors_uptime_by_pidgraph_ids(self, pidgraph_ids: str) -> str:
        monitor_ids = []
        with dbm.open(settings.uptime_monitors_mapping_db, 'r') as db:
            for pidgraph_id in pidgraph_ids.split('-'):
                try:
                    monitor_ids.append(db[pidgraph_id].decode('utf-8'))
                except KeyError:
                    logger.error(f"PID Graph ID not found in UptimeRobot mapping: {pidgraph_id}")
                    continue
        return self.get_monitors_mean_uptime(monitor_ids)

    def get_monitors_mean_uptime(self, monitor_ids: List[str]) -> str:
        httpx_client = httpx.Client(headers={"user-agent": settings.PIDRESOLVER_USER_AGENT,
                                             "Content-Type": "application/x-www-form-urlencoded"})

        now = datetime.datetime.now()
        oneyearago = now - relativedelta(years=1)
        days_in_last_year = (now - oneyearago).days

        time_range = f'{int(oneyearago.timestamp())}_{int(now.timestamp())}'
        payload = f'api_key={self.uptimerobot_api_key}&format=json&logs=0&monitors={"-".join(monitor_ids)}&custom_uptime_ranges={time_range}'
        logger.debug(payload)
        response = httpx_client.post('https://api.uptimerobot.com/v2/getMonitors', data=payload)
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
    uptimerobo = UptimeRobot()
    uptimerobo.update_monitors_mapping()

    db = dbm.open(settings.uptime_monitors_mapping_db, 'r')
    for key in db.keys():
        value = db[key]
        print(f'"{key.decode('utf-8')}" :  "{value.decode('utf-8')}"')
    db.close()


        # jsonpath_expr = parse('$.mean_uptime')
        # # Find the mean_uptime
        # mean_uptime = [match.value for match in jsonpath_expr.find(data)][0]
