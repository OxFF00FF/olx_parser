import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    USE_PROXY: bool = None
    PROXY: str = None
    DEBUG: bool
    MAX_WORKERS: int

    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))


app_config: Config = Config()
