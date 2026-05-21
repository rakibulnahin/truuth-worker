from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Truuth Worker"
    app_version: str = "0.1.0"
    environment: str = "local"
    repository_backend: Literal["memory", "mongo", "postgres"] = "memory"
    mongodb_uri: str | None = Field(default=None, alias="MONGODB_URI")
    mongodb_database: str = "truuth_worker_demo"
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
