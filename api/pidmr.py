from schemas.schemas import PIDMResolutionEvent


def save_pidmr_event(event: PIDMResolutionEvent) -> dict:
    # TODO: implement
    return {"Event": event.pid_id}
