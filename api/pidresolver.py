from datetime import datetime
from typing import Optional

import httpx
import idutils
from pydantic import BaseModel

from settings import settings


class ResolutionRecord(BaseModel):
    time_stamp: datetime
    pid_id: str
    pid_url: str
    status_code: Optional[int]
    ssl_verified: bool
    redirect_count: Optional[int]
    resolution_url: Optional[str]
    http_error: Optional[str]


def get_resolved_pid_record(pid: str) -> Optional[ResolutionRecord]:
    """Resolve a persistent identifier (PID) and return a ResolutionRecord object with information about the
    resolution process."""
    id_scheme = idutils.detect_identifier_schemes(pid)
    if not any(id_scheme):
        return None
        # TODO: "Identifier scheme not recognised": Add logging, do not write to the database

    pidx = idutils.to_url(pid, id_scheme[0])
    if pidx.lower().startswith("http:") and pid.lower().startswith("https:"):
        # idutils returns http:// instead of https://doi.org and will therefore invoke one more additional redirect
        # than the original pid would have done. So we correct this here.
        pidx = pidx.replace("http:", "https:")

    respons, verified, error = resolve_pid(pidx, True)
    return create_resolution_record(pid, pidx, respons, verified, error)


def create_resolution_record(pid: str, pidx: str, response: Optional[httpx.Response], verified: bool,
                             error: Optional[str]) -> ResolutionRecord:
    """Create a ResolutionRecord based on the PID resolution response."""
    return ResolutionRecord(
        time_stamp=datetime.now(),
        pid_id=pid,
        pid_url=pidx,
        status_code=response.status_code if response else None,
        ssl_verified=verified,
        redirect_count=len(response.history) if response else None,
        resolution_url=str(response.url) if response else None,
        http_error=str(error) if response is None else None
    )


def resolve_pid(pid: str, verify: bool) -> tuple[Optional[httpx.Response], bool, Optional[str]]:
    """Attempt to resolve the PID with HTTP requests, following redirects and verifying SSL."""

    # https://www.python-httpx.org/advanced/timeouts/
    # There are four different types of timeouts that may occur. These are connect, read, write, and pool timeouts.
    # The default behavior is to raise a TimeoutException after 5 seconds of network inactivity.
    client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(settings.PIDRESOLVER_TIMEOUT, read=settings.PIDRESOLVER_READ_TIMEOUT), verify=verify,
                          max_redirects=settings.PIDRESOLVER_MAX_REDIR,
                          headers={"user-agent": settings.PIDRESOLVER_USER_AGENT})
    try:
        response = client.get(pid)
        return response, verify, None
    except httpx.HTTPError as error:  # See: https://www.python-httpx.org/exceptions/ & https://www.python-httpx.org/quickstart/#exceptions
        if verify:
            return resolve_pid(pid, False)
        else:
            return None, False, error.__str__()


if __name__ == "__main__":
    #
    print(settings.PIDRESOLVER_USER_AGENT)
    pids = ["http://hdl.handle.net/10261/231953", "http://dx.doi.org/10.20350/digitalCSIC/8615",
            "http://hdl.handle.net/10261/231860", "http://hdl.handle.net/10261/231993",
            "http://hdl.handle.net/10261/235890",
            "http://dx.doi.org/10.20350/digitalCSIC/8960", "http://hdl.handle.net/10261/235967",
            "http://hdl.handle.net/10261/231753", "http://hdl.handle.net/10261/235934",
            "http://hdl.handle.net/10261/216881",
            "http://dx.doi.org/10.20350/digitalCSIC/13835", "http://hdl.handle.net/10261/236026",
            "http://dx.doi.org/10.20350/digitalCSIC/13782", "http://hdl.handle.net/10261/231894",
            "http://dx.doi.org/10.20350/digitalCSIC/13680",
            "http://hdl.handle.net/10261/231953", "http://fshhstrjhfjhkk.org/10.20350/digitalCSIC/8615",
            "https://doi.org/10.25606/SURF.578c6039-0efb60b8", "https://doi.org/10.25606/SURF.578c6039-8f766ac7",
            "https://doi.org/10.25606/SURF.578c6039-0c8c9310", "https://doi.org/10.25606/SURF.578c6039-6dbee678",
            "https://doi.org/10.25606/SURF.578c6039-a71f8bdc", "https://doi.org/10.25606/SURF.578c6039-22c5c9fd",
            "https://doi.org/10.25606/SURF.636f736d6f67-44", "https://doi.org/10.25606/SURF.578c6039-25cfab2c",
            "https://zenodo.org/doi/10.5281/zenodo.4672413", "https://doi.org/10.25606/SURF.578c6039-f84d9032"]
    for pid in pids:
        print(pid)
        print(get_resolved_pid_record(pid))
