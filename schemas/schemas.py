from datetime import datetime
from enum import StrEnum, unique, auto
from typing import List
from pydantic import ConfigDict, BaseModel

@unique
class PIDMODE(StrEnum):
    LANDINGPAGE = "landingpage"
    METADATA = "metadata"
    RESOURCE = "resource"


class Pid(BaseModel):
    pids: List[str]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pids": ["https://doi.org/10.15167/tomasi-federico_phd2019-03-14", "10.5281/zenodo.4672413"]
        }
    })


class PIDMResolutionEvent(BaseModel):
    time_stamp: datetime
    pid_id: str
    pid_mode: PIDMODE
    pid_type: str
    pid_endpoint: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "time_stamp": "2022-01-01T00:00:00",
            "pid_id": "10.5281/zenodo.4672413",
            "pid_mode": PIDMODE.LANDINGPAGE.value,
            "pid_type": "doi",
            "pid_endpoint": "https://doi.org/10.5281/zenodo.4672413"
        }
    })


class PIDMResolutionRecord(BaseModel):
    time_stamp: datetime
    pid_id: str
    pid_url: str
    status_code: str
    ssl_verified: bool
    redirect_count: int
    resolution_url: str
    http_error: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1,
            "time_stamp": "2022-01-01T00:00:00",
            "pid_id": "10.5281/zenodo.4672413",
            "pid_url": "https://doi.org/10.5281/zenodo.4672413",
            "status_code": "200",
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
    timestamp: datetime
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "janedoe",
            "disabled": False,
            "timestamp": "2024-07-30 00:00:00"
        }
    })
