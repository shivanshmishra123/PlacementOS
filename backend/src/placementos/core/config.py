"""PlacementOS Settings and Configuration."""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Authoritative application settings validated from environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime Environment
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = Field(
        default="dev_secret_key_placementos_must_be_at_least_32_chars_long",
        description="Secret key used for HMAC and session hashing.",
    )
    SESSION_COOKIE_NAME: str = "placementos_session"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 24 hours

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://placementos:placementos_dev_password@localhost:55432/placementos",
        description="SQLAlchemy PostgreSQL connection string.",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Private Object Storage (S3 / MinIO)
    S3_ENDPOINT_URL: str = "http://localhost:4566"
    S3_ACCESS_KEY_ID: str = "dev_access_key"
    S3_SECRET_ACCESS_KEY: str = "dev_secret_key"
    S3_BUCKET_NAME: str = "placementos-dev"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False

    # Email Transport (Mailpit local sink in dev)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_SENDER: str = "noreply@placementos.local"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False

    # CORS & Web
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v


# Cached global settings instance
settings = Settings()
