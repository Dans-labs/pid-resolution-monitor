from fastapi import APIRouter

from celeryworker.utils import get_task_info

router = APIRouter(
    tags=["Celery"],
    responses={404: {"description": "Not found"}},
)


@router.get("/task/{task_id}", summary="Get the status of a Celery Task", include_in_schema=False)
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of a Celery TaskId
    """
    return get_task_info(task_id)
