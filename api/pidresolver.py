from datetime import datetime
from typing import Optional

import httpx
import idutils
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential_jitter, \
    RetryError

from logging_config import prm_logger as logger
from settings import settings


class ResolutionRecord(BaseModel):
    time_stamp: datetime
    pid_id: str
    pid_url: str
    status_code: Optional[int]
    content_type: Optional[str]
    ssl_verified: bool
    redirect_count: Optional[int]
    resolution_url: Optional[str]
    http_error: Optional[str]


def get_actionable_pid_url(pid: str) -> Optional[str]:
    id_scheme = idutils.detect_identifier_schemes(pid)
    if not id_scheme:
        logger.warn(f"Identifier scheme not recognised: {pid}")
        return None
    pidx = idutils.to_url(pid, id_scheme[0])
    if pidx.lower().startswith("http:") and pid.lower().startswith("https:"):
        pidx = pidx.lower().replace("http:", "https:")
    return pidx


def resolve_url_by_pid(pid: str) -> Optional[ResolutionRecord]:
    """Resolves a persistent identifier (PID) in any form. Returns a (PID) ResolutionRecord object with the resolution results.
    :rtype: ResolutionRecord"""
    pidx = get_actionable_pid_url(pid)
    if not pidx:
        return None
    try:
        response, verified, error = resolve_pid(pidx, True)
        return create_resolution_record(pid, pidx, response, verified, error)
    except RetryError as e:
        raise e.last_attempt.exception()  # Tenacity back-off failed. Raise the last Exception, so that the task can be rescheduled.


def create_resolution_record(pid: str, pidx: str, response: Optional[httpx.Response], verified: bool,
                             error: Optional[str]) -> ResolutionRecord:
    """Create a ResolutionRecord based on the PID resolution response.
    :rtype: ResolutionRecord
    """
    return ResolutionRecord(
        time_stamp=datetime.now(),
        pid_id=pid,
        pid_url=pidx,
        status_code=response.status_code if response else None,
        content_type=response.headers.get("Content-Type") if response else None,
        ssl_verified=verified,
        redirect_count=len(response.history) if response else None,
        resolution_url=str(response.url) if response else None,
        http_error=str(error) if response is None else None
    )


@retry(
    wait=wait_exponential_jitter(initial=2, jitter=1.5),
    stop=stop_after_attempt(2),
    retry=retry_if_exception_type(httpx.HTTPError)
)
def resolve_pid(pid: str, verify: bool) -> tuple[Optional[httpx.Response], bool, Optional[str]]:
    """Attempt to resolve the PID, following redirects, bypassing SSL validation if needed."""

    # https://www.python-httpx.org/advanced/timeouts/
    # There are four different types of timeouts that may occur. These are connect, read, write, and pool timeouts.
    # The default behavior is to raise a TimeoutException after 5 seconds of network inactivity.
    client = httpx.Client(follow_redirects=True,
                          timeout=httpx.Timeout(settings.PIDRESOLVER_TIMEOUT, read=settings.PIDRESOLVER_READ_TIMEOUT),
                          verify=verify,
                          max_redirects=settings.PIDRESOLVER_MAX_REDIR,
                          headers={"user-agent": settings.PIDRESOLVER_USER_AGENT})
    try:
        response = client.get(pid)
        return response, verify, None
    except httpx.HTTPError as error:  # See: https://www.python-httpx.org/exceptions/ & https://www.python-httpx.org/quickstart/#exceptions
        if verify:
            return resolve_pid(pid, False)
        else:
            raise error
