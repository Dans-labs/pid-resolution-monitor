from dynaconf import Dynaconf

settings = Dynaconf(
    settings_files=["config/settings.toml"],
    secrets=["config/.secrets.toml"],
    environments=True,
    default_env="default",
    load_dotenv=True
)
