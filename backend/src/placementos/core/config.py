"""PlacementOS Settings and Configuration."""

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OIDC_ADAPTER_IMPLEMENTED = False
CLAMAV_ADAPTER_IMPLEMENTED = False


class Settings(BaseSettings):
    """Authoritative application settings validated from environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="PLACEMENTOS_",
        extra="ignore",
    )

    # Runtime Environment
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    RELEASE_VERSION: str = "0.12.0"

    # Security
    SECRET_KEY: str = Field(
        default="dev_secret_key_placementos_must_be_at_least_32_chars_long",
        description="Secret key used for HMAC and session hashing.",
    )
    SESSION_COOKIE_NAME: str = "placementos_session"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 24 hours
    IDENTITY_MODE: Literal["development_personas", "oidc"] = "development_personas"
    OIDC_ISSUER_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_MEMBERSHIP_OWNER: str = ""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://placementos_app:placementos_app_dev_password@127.0.0.1:55432/placementos",
        description="SQLAlchemy PostgreSQL connection string.",
    )
    MIGRATION_DATABASE_URL: str = Field(
        default="postgresql+psycopg://placementos:placementos_dev_password@127.0.0.1:55432/placementos",
        description="Privileged URL used only by Alembic and administrative migration commands.",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis & Celery
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"

    # Trusted LangGraph checkpoint role/schema (never exposed to clients)
    WORKFLOW_DATABASE_URL: str = (
        "postgresql://placementos_workflow:placementos_workflow_dev_password@127.0.0.1:55432/"
        "placementos?options=-csearch_path%3Dworkflow_checkpoints"
    )

    # Private Object Storage (S3 / MinIO)
    S3_ENDPOINT_URL: str = "http://127.0.0.1:4566"
    S3_ACCESS_KEY_ID: str = "dev_access_key"
    S3_SECRET_ACCESS_KEY: str = "dev_secret_key"
    S3_BUCKET_NAME: str = "placementos-dev"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False
    MALWARE_SCANNER_MODE: Literal["development_fixture", "clamav"] = "development_fixture"
    MODEL_INTERPRETER_MODE: Literal["fixture", "disabled"] = "fixture"
    MODEL_PROVIDER_NAME: str = ""
    MODEL_ID: str = ""
    MODEL_DATA_REGION: str = ""
    MODEL_POLICY_REVIEWED: bool = False
    MODEL_MAX_CALLS_PER_DRIVE: int = 10
    MODEL_MAX_INPUT_TOKENS_PER_DRIVE: int = 100_000
    EXCEPTION_PLANNER_MODE: Literal["fixture", "disabled"] = "fixture"
    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    MAX_PDF_PAGES: int = 50
    MAX_EXTRACTED_TEXT_CHARS: int = 2_000_000

    # Email Transport (Mailpit local sink in dev)
    SMTP_HOST: str = "127.0.0.1"
    SMTP_PORT: int = 1025
    SMTP_SENDER: str = "noreply@placementos.local"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False
    EMAIL_ADAPTER_MODE: Literal["mailpit", "smtp", "disabled"] = "mailpit"
    EMAIL_RECIPIENT_ALLOWLIST_DOMAINS: list[str] = ["apex.edu", "beacon.edu"]
    EMAIL_SEND_TIMEOUT_SECONDS: int = 10
    LIVE_SEND_ENABLED: bool = False
    PRODUCTION_SENDER_VERIFIED: bool = False
    PUBLIC_WEB_URL: str = "http://localhost:3000"

    # Google Workspace connectors (P11). Tokens remain encrypted server-side.
    GOOGLE_CONNECTORS_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/google/callback"
    INTEGRATION_TOKEN_ENCRYPTION_KEY: str = ""
    GOOGLE_OAUTH_AUTHORIZE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_OAUTH_REVOKE_URL: str = "https://oauth2.googleapis.com/revoke"
    GOOGLE_API_TIMEOUT_SECONDS: int = 20
    INTEGRATION_WEBHOOK_BASE_URL: str = ""

    # Institution-owned pilot configuration. Empty values deliberately block real-data readiness.
    INSTITUTION_TIMEZONE_CONFIRMED: bool = False
    ACADEMIC_CONFIGURATION_REVIEWED: bool = False
    PERMISSIONS_MATRIX_REVIEWED: bool = False
    RETENTION_POLICY_ID: str = ""
    RECORD_RETENTION_DAYS: int | None = None
    BACKUP_RETENTION_DAYS: int | None = None
    DELETION_OWNER: str = ""
    DEPLOYMENT_REGION: str = ""
    OPERATIONS_OWNER: str = ""
    SECURITY_OWNER: str = ""
    BACKUP_OWNER: str = ""
    INCIDENT_CONTACT: str = ""
    BACKUP_ENCRYPTION_KEY_ID: str = ""
    BACKUP_RESTORE_TESTED: bool = False

    # CORS & Web
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @field_validator("MALWARE_SCANNER_MODE")
    @classmethod
    def validate_scanner_mode(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v == "development_fixture":
            raise ValueError("Production requires a real malware scanner adapter")
        return v

    @field_validator("MODEL_INTERPRETER_MODE")
    @classmethod
    def validate_model_mode(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v == "fixture":
            raise ValueError("Production cannot use the deterministic model fixture")
        return v

    @field_validator("EMAIL_ADAPTER_MODE")
    @classmethod
    def validate_email_adapter(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v == "mailpit":
            raise ValueError("Production cannot use the Mailpit development adapter")
        return v

    @field_validator("PUBLIC_WEB_URL")
    @classmethod
    def validate_public_web_url(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v.startswith("https://"):
            raise ValueError("Production PUBLIC_WEB_URL must use HTTPS")
        return v.rstrip("/")

    @field_validator("WORKFLOW_DATABASE_URL")
    @classmethod
    def validate_workflow_database_url(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and "_dev_password" in v:
            raise ValueError("Production requires a separately provisioned workflow database role")
        return v

    @model_validator(mode="after")
    def production_must_not_masquerade_as_ready(self) -> "Settings":
        """Fail startup when production selects unsafe development identities or effects."""
        if self.ENVIRONMENT != "production":
            return self
        errors: list[str] = []
        if self.DEBUG:
            errors.append("DEBUG must be disabled")
        if (
            self.SECRET_KEY.startswith("dev_")
            or "placementos" in self.SECRET_KEY.lower()
            or "replace" in self.SECRET_KEY.lower()
        ):
            errors.append("SECRET_KEY must be externally generated")
        if (
            self.IDENTITY_MODE != "oidc"
            or not self.OIDC_ISSUER_URL.startswith("https://")
            or not self.OIDC_CLIENT_ID
        ):
            errors.append("OIDC identity configuration is required")
        if not self.OIDC_MEMBERSHIP_OWNER:
            errors.append("OIDC membership ownership is required")
        if self.MALWARE_SCANNER_MODE != "clamav":
            errors.append("a real malware scanner is required")
        if self.EXCEPTION_PLANNER_MODE == "fixture":
            errors.append("production cannot use the deterministic exception-planner fixture")
        if not OIDC_ADAPTER_IMPLEMENTED:
            errors.append("the production OIDC adapter is not implemented")
        if not CLAMAV_ADAPTER_IMPLEMENTED:
            errors.append("the production ClamAV adapter is not implemented")
        if "_dev_password" in self.DATABASE_URL or "_dev_password" in self.MIGRATION_DATABASE_URL:
            errors.append("production database roles must use externally provisioned credentials")
        if (
            not self.S3_ENDPOINT_URL.startswith("https://")
            or self.S3_ACCESS_KEY_ID.startswith("dev_")
            or self.S3_BUCKET_NAME == "placementos-dev"
        ):
            errors.append("private production object storage is required")
        if self.EMAIL_ADAPTER_MODE == "smtp" and (
            not self.LIVE_SEND_ENABLED or not self.PRODUCTION_SENDER_VERIFIED
        ):
            errors.append("live SMTP requires an explicitly verified sender and enable flag")
        if self.GOOGLE_CONNECTORS_ENABLED and (
            not self.GOOGLE_CLIENT_ID
            or not self.GOOGLE_CLIENT_SECRET
            or not self.GOOGLE_REDIRECT_URI.startswith("https://")
            or not self.INTEGRATION_TOKEN_ENCRYPTION_KEY
            or "replace" in self.INTEGRATION_TOKEN_ENCRYPTION_KEY.lower()
        ):
            errors.append(
                "enabled Google connectors require OAuth credentials, an HTTPS redirect, and an external token-encryption key"
            )
        if not self.RETENTION_POLICY_ID or not self.RECORD_RETENTION_DAYS or not self.DELETION_OWNER:
            errors.append("an institution retention policy is required")
        if not self.BACKUP_RETENTION_DAYS or not self.BACKUP_ENCRYPTION_KEY_ID:
            errors.append("encrypted backup retention is required")
        if not self.DEPLOYMENT_REGION:
            errors.append("deployment region is required")
        if not all(
            [self.OPERATIONS_OWNER, self.SECURITY_OWNER, self.BACKUP_OWNER, self.INCIDENT_CONTACT]
        ):
            errors.append("named operational, security, backup, and incident owners are required")
        pilot_strings = [
            self.OIDC_ISSUER_URL,
            self.OIDC_CLIENT_ID,
            self.OIDC_MEMBERSHIP_OWNER,
            self.DATABASE_URL,
            self.MIGRATION_DATABASE_URL,
            self.WORKFLOW_DATABASE_URL,
            self.S3_ENDPOINT_URL,
            self.S3_ACCESS_KEY_ID,
            self.S3_SECRET_ACCESS_KEY,
            self.S3_BUCKET_NAME,
            self.PUBLIC_WEB_URL,
            self.RETENTION_POLICY_ID,
            self.DELETION_OWNER,
            self.DEPLOYMENT_REGION,
            self.OPERATIONS_OWNER,
            self.SECURITY_OWNER,
            self.BACKUP_OWNER,
            self.INCIDENT_CONTACT,
            self.BACKUP_ENCRYPTION_KEY_ID,
        ]
        if any("replace" in value.lower() or "example." in value.lower() for value in pilot_strings):
            errors.append("placeholder pilot values must be replaced")
        if any(not origin.startswith("https://") for origin in self.ALLOWED_ORIGINS):
            errors.append("production browser origins must use HTTPS")
        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self


# Cached global settings instance
settings = Settings()
