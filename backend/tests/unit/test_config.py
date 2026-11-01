"""Tests for Settings and Validation."""

import pytest

from placementos.core.config import Settings


def test_settings_default_values():
    """Verify default development configuration is safe and complete."""
    settings = Settings()
    assert settings.ENVIRONMENT in ["development", "test", "production"]
    assert settings.API_V1_PREFIX == "/api/v1"
    assert len(settings.SECRET_KEY) >= 32
    assert "postgresql" in settings.DATABASE_URL


def test_secret_key_minimum_length_validation():
    """Verify SECRET_KEY shorter than 32 characters raises ValidationError."""
    with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters long"):
        Settings(SECRET_KEY="too-short")


def test_production_rejects_development_scanner_fixture():
    """Production must fail closed when only the development scanner is configured."""
    with pytest.raises(ValueError, match="real malware scanner"):
        Settings(
            ENVIRONMENT="production",
            MALWARE_SCANNER_MODE="development_fixture",
            MODEL_INTERPRETER_MODE="disabled",
        )


def test_production_rejects_deterministic_model_fixture():
    """The deterministic P04 adapter must never impersonate a production model provider."""
    with pytest.raises(ValueError, match="deterministic model fixture"):
        Settings(
            ENVIRONMENT="production",
            MALWARE_SCANNER_MODE="clamav",
            MODEL_INTERPRETER_MODE="fixture",
        )


def test_production_rejects_mailpit_transport():
    """The development sink cannot silently become a production mail adapter."""
    with pytest.raises(ValueError, match="Mailpit development adapter"):
        Settings(
            ENVIRONMENT="production",
            MALWARE_SCANNER_MODE="clamav",
            MODEL_INTERPRETER_MODE="disabled",
            EMAIL_ADAPTER_MODE="mailpit",
        )


def test_production_rejects_missing_identity_and_operational_owners():
    """Production cannot start with development identity or anonymous operational ownership."""
    with pytest.raises(ValueError, match="OIDC identity configuration is required"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="externally-generated-secret-key-with-64-safe-characters-1234567890",
            MALWARE_SCANNER_MODE="clamav",
            MODEL_INTERPRETER_MODE="disabled",
            EMAIL_ADAPTER_MODE="disabled",
            PUBLIC_WEB_URL="https://placement.example.edu",
            WORKFLOW_DATABASE_URL="postgresql://workflow:external@db/placementos",
            DATABASE_URL="postgresql+psycopg://app:external@db/placementos",
            MIGRATION_DATABASE_URL="postgresql+psycopg://migration:external@db/placementos",
            S3_ENDPOINT_URL="https://objects.apex.edu",
            S3_ACCESS_KEY_ID="external-access-key",
            S3_SECRET_ACCESS_KEY="external-secret-key",
            S3_BUCKET_NAME="placementos-pilot-private",
            ALLOWED_ORIGINS=["https://placement.apex.edu"],
            RETENTION_POLICY_ID="RET-2026-01",
            RECORD_RETENTION_DAYS=365,
            BACKUP_RETENTION_DAYS=30,
            BACKUP_ENCRYPTION_KEY_ID="kms/placementos-backups",
            DELETION_OWNER="records@example.edu",
            DEPLOYMENT_REGION="in-south",
            OPERATIONS_OWNER="placement-ops@example.edu",
            SECURITY_OWNER="security@example.edu",
            BACKUP_OWNER="platform@example.edu",
            INCIDENT_CONTACT="soc@example.edu",
        )


def test_production_config_cannot_claim_unimplemented_runtime_adapters():
    with pytest.raises(ValueError, match="production OIDC adapter is not implemented"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="externally-generated-secret-key-with-64-safe-characters-1234567890",
            IDENTITY_MODE="oidc",
            OIDC_ISSUER_URL="https://identity.apex.edu",
            OIDC_CLIENT_ID="placementos",
            OIDC_MEMBERSHIP_OWNER="identity-team@apex.edu",
            DATABASE_URL="postgresql+psycopg://app:external@db/placementos",
            MIGRATION_DATABASE_URL="postgresql+psycopg://migration:external@db/placementos",
            MALWARE_SCANNER_MODE="clamav",
            MODEL_INTERPRETER_MODE="disabled",
            EMAIL_ADAPTER_MODE="disabled",
            PUBLIC_WEB_URL="https://placement.apex.edu",
            ALLOWED_ORIGINS=["https://placement.apex.edu"],
            WORKFLOW_DATABASE_URL="postgresql://workflow:external@db/placementos",
            S3_ENDPOINT_URL="https://objects.apex.edu",
            S3_ACCESS_KEY_ID="external-access-key",
            S3_SECRET_ACCESS_KEY="external-secret-key",
            S3_BUCKET_NAME="placementos-pilot-private",
            RETENTION_POLICY_ID="RET-2026-01",
            RECORD_RETENTION_DAYS=365,
            BACKUP_RETENTION_DAYS=30,
            BACKUP_ENCRYPTION_KEY_ID="kms/placementos-backups",
            DELETION_OWNER="records@apex.edu",
            DEPLOYMENT_REGION="in-south",
            OPERATIONS_OWNER="placement-ops@apex.edu",
            SECURITY_OWNER="security@apex.edu",
            BACKUP_OWNER="platform@apex.edu",
            INCIDENT_CONTACT="soc@apex.edu",
        )
