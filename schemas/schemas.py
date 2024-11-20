from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, unique
from typing import List

from pydantic import ConfigDict, BaseModel


@unique
class PidmrMode(StrEnum):
    LANDINGPAGE = "landingpage"
    METADATA = "metadata"
    RESOURCE = "resource"


@dataclass
class UptimemonitorMapping:
    pid_graph_id: str
    local_id: str
    monitor_name: str


class Pid(BaseModel):
    pids: List[str]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pids": ["http://hdl.handle.net/10261/201090", "10.5281/zenodo.4672413",
                     "https://hdl.handle.net/11245/1.132038"]
        }
    })


class PidMrEventRecord(BaseModel):
    id: int | None = None
    time_stamp: datetime
    pid_id: str
    pid_mode: PidmrMode
    pid_type: str
    pid_endpoint: str
    pid_resolver_status: int | None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "time_stamp": "2022-01-01T00:00:00",
            "pid_id": "10.5281/zenodo.4672413",
            "pid_mode": PidmrMode.LANDINGPAGE.value,
            "pid_type": "doi",
            "pid_endpoint": "https://doi.org/10.5281/zenodo.4672413",
            "pid_resolver_status": 200
        }
    })


class BatchPids(BaseModel):
    batch_id: int
    total_pids: int
    offset: int
    limit: int
    pids: List[str]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "batch_id": 1,
            "total_pids": 50000,
            "offset": 0,
            "limit": 2,
            "pids": ["http://hdl.handle.net/10261/201090", "10.5281/zenodo.4672413",
                     "https://hdl.handle.net/11245/1.132038"]
        }
    })


class PidBaseBatch(BaseModel):
    batch_id: int
    total_pids: int
    identifier_type: str | None = None
    actor: str
    institution: str
    description: str | None = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "batch_id": 1,
            "total_pids": 2,
            "identifier_type": "pid_graph:1A718108",
            "actor": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0",
            "description": "This sample batch checks the resolution of a PID."
        }
    })


class PidUpdateBatch(BaseModel):
    batch_id: int
    pids_added: int
    total_pids: int
    identifier_type: str
    actor: str
    institution: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "batch_id": 1,
            "pids_added": 1,
            "total_pids": 2,
            "identifier_type": "pid_graph:1A718108",
            "actor": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0"
        }
    })


class PidResolutionBaseBatch(BaseModel):
    sample_pids: List[str]
    identifier_type: str | None = None
    actor: str
    institution: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "sample_pids": ["http://hdl.handle.net/10261/201090", "10.5281/zenodo.4672413"],
            "identifier_type": "pid_graph:1A718108",
            "actor": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0"
        }
    })


class PidResolutionUpdateBatch(PidResolutionBaseBatch):
    id: int | None = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1,
            "sample_pids": ["http://hdl.handle.net/10261/201090", "10.5281/zenodo.4672413"],
            "identifier_type": "pid_graph:1A718108",
            "actor": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0"
        }
    })


class PidResolutionCreateBatch(PidResolutionBaseBatch):
    id: int | None = None
    description: str | None = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "sample_pids": ["https://hdl.handle.net/11245/1.132038", "10.5281/zenodo.4672413"],
            "identifier_type": "pid_graph:1A718108",
            "actor": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0",
            "description": "This sample batch checks the resolution of a PID."
        }
    })


class PidResolutionRecord(BaseModel):
    time_stamp: datetime
    pid_id: str
    pid_url: str
    status_code: int | None
    content_type: str | None
    ssl_verified: bool
    redirect_count: int | None
    resolution_url: str | None
    http_error: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "time_stamp": "2022-01-01T00:00:00",
            "pid_id": "10.5281/zenodo.4672413",
            "pid_url": "https://doi.org/10.5281/zenodo.4672413",
            "status_code": 200,
            "content_type": "text/html; charset=utf-8",
            "ssl_verified": True,
            "redirect_count": 4,
            "resolution_url": "https://iris.unige.it//handle/11567/941700",
            "http_error": "None"
        }
    })


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    disabled: bool | None = None
    time_stamp: datetime
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "janedoe",
            "disabled": False,
            "time_stamp": "2024-07-30 00:00:00"
        }
    })


class Monitor(BaseModel):
    id: int
    pid_graph_id: str
    friendly_name: str
    url: str
    uptime: str


class UptimeMonitorsRequest(BaseModel):
    actor: str
    identifier: str
    institution: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "actor": "pid_graph:1A718108",
            "identifier": "pid_graph:3E6F3EE6",
            "institution": "pid_graph:258448F0"
        }})


class UptimeResponse(BaseModel):
    stat: str
    mean_uptime: float
    days_downtime: float
    timestamp_interval: str
    monitors: List[Monitor]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stat": "ok",
            "mean_uptime": 99.9855,
            "days_downtime": 0.0145,
            "timestamp_interval": "1694931505_1726553905",
            "monitors": [
                {
                    "id": 797637034,
                    "pid_graph_id": "pid_graph:E2045F7A",
                    "friendly_name": "arXiv",
                    "url": "http://arXiv.org/openurl-resolver?id=oai%3AarXiv.org%3Acs.DL%2F0106057",
                    "uptime": "99.971"
                }
            ]
        }
    })
