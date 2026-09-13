"""Application settings from environment."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "dev-secret-change-me-in-production"
    DATABASE_URL: str = "sqlite:///./db/db.sqlite"
    ENROLLMENT_KEY: str = "dev-enrollment-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
    LOG_LEVEL: str = "INFO"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    MAX_RESULT_BYTES: int = 2_000_000
    SESSION_IDLE_TIMEOUT: int = 1800  # seconds

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
