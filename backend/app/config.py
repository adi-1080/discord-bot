import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    discord_application_id: str = ""
    discord_public_key: str = ""
    discord_bot_token: str = ""

    database_url: str = "postgresql+asyncpg://localhost/abstrabit"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"

    app_url: str = "http://localhost:8000"
    environment: str = "development"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Ensure Neon/libpq URLs work with SQLAlchemy async + asyncpg."""
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value.removeprefix("postgres://")
        elif value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        elif value.startswith("postgresql+psycopg2://"):
            value = "postgresql+asyncpg://" + value.removeprefix("postgresql+psycopg2://")

        value = value.replace("sslmode=require", "ssl=require")
        value = value.replace("sslmode=verify-full", "ssl=require")
        value = re.sub(r"[?&]channel_binding=[^&]*", "", value)
        value = value.replace("?&", "?").rstrip("?&")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
