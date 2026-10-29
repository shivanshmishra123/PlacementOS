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
