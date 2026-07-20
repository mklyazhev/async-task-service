from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    rabbitmq_url: str
    outbox_batch_size: int = 20
    outbox_poll_interval_seconds: float = 1.0
    task_execution_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
