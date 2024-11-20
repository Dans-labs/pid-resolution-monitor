from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["config/settings.toml"],
    environments=True,
    default_env="default",
    load_dotenv=True
)
# Seems Dynaconf lazy-loads dotenv file?
# So we call "a" setting here to ensure that the .env settings are loaded at the start of the application.
settings.FASTAPI_VERSION
