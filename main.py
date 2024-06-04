import time

import uvicorn as uvicorn
from dynaconf import Dynaconf
from fastapi import FastAPI

from config.celery_utils import create_celery
from routers import pidresolution


def create_app() -> FastAPI:
    settings = Dynaconf(settings_files=["config/settings.toml"], secrets=["config/.secrets.toml"], environments=True, default_env="default", load_dotenv=True)
    current_app = FastAPI(title=settings.fastapi_title, description=settings.fastapi_description, version=settings.fastapi_version, )

    current_app.celery_app = create_celery()
    current_app.include_router(pidresolution.router)
    return current_app


app = create_app()
celery = app.celery_app


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(f'{process_time:0.4f} sec')
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", port=9000, reload=True)
