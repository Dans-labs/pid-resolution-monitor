import time
from contextlib import asynccontextmanager

import emoji
import uvicorn as uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from celeryworker.utils import create_celery
from database import models
from database.database import engine
from routers import pidresolution, pidmr
from settings import settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    print(f'Created DB metadata...{emoji.emojize(':high_voltage:')}')
    yield  # before the yield, will be executed before the application starts
    print(f'Stopping DB connectionpool...{emoji.emojize(':bomb:')}')


def create_app() -> FastAPI:
    current_app = FastAPI(title=settings.fastapi_title, description=settings.fastapi_description, version=settings.fastapi_version, lifespan=lifespan)

    current_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    current_app.celery_app = create_celery()
    current_app.include_router(pidresolution.router)
    current_app.include_router(pidmr.router)
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
