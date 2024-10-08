import os
from functools import lru_cache

from kombu import Queue


def route_task(name, args, kwargs, options, task=None, **kw):
    """Routes/maps a task to a certain queue by its (task)name"""
    if ":" in name:
        queue, _ = name.split(":")
        return {"queue": queue}
    return {"queue": "celery"}  # Add to the default queue: 'celery'


class BaseConfig:

    CELERY_broker_url: str = os.environ.get("CELERY_BROKER_URL", "amqp://user:password@localhost:5672//")
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#conf-database-result-backend
    result_backend: str = os.environ.get("result_backend", "rpc://")
    task_ignore_result = True

    # These queues will all be created if the celey worker was not started with the -Q option:
    CELERY_TASK_QUEUES: list = (
        Queue("celery"),  # default queue
        # custom queues:
        Queue("pidmr"),
        Queue("pid-resolution"),
    )

    CELERY_TASK_ROUTES = (route_task,)


class DevelopmentConfig(BaseConfig):
    pass


@lru_cache()
def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
    }
    config_name = os.environ.get("CELERY_CONFIG", "development")

    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()
