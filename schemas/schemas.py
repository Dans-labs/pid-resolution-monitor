from typing import List, Optional
from datetime import datetime
from pydantic import ConfigDict, BaseModel

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
    pid_type: str
    pid_endpoint: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "time_stamp": "2022-01-01T00:00:00",
            "pid_id": "10.5281/zenodo.4672413",
            "pid_type": "doi",
            "pid_endpoint": "https://doi.org/10.5281/zenodo.4672413"
        }
    })
