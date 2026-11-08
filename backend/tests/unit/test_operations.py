"""P10 privacy-safe operational readiness projections."""

from placementos.core.config import Settings
from placementos.services.operations import pilot_readiness_snapshot


def test_development_readiness_is_honestly_synthetic_only():
    snapshot = pilot_readiness_snapshot(Settings(_env_file=None))
    assert snapshot["synthetic_demo_ready"] is True
    assert snapshot["real_data_pilot_ready"] is False
    assert snapshot["status"] == "synthetic_demo_only"
    assert "oidc_identity" in snapshot["blockers"]
    assert snapshot["development_adapters"] == {
        "identity": True,
        "scanner": True,
        "model": True,
        "mail": True,
    }


def test_readiness_projection_does_not_expose_secrets():
    config = Settings(
        _env_file=None,
        SECRET_KEY="never-return-this-secret-value-1234567890",
        SMTP_PASSWORD="never-return-this-password",
        S3_SECRET_ACCESS_KEY="never-return-this-object-secret",
    )
    serialized = str(pilot_readiness_snapshot(config))
    assert "never-return-this" not in serialized
    assert "SMTP_PASSWORD" not in serialized
    assert "S3_SECRET_ACCESS_KEY" not in serialized


def test_configuration_cannot_substitute_for_missing_production_adapters(monkeypatch):
    import placementos.services.operations

    monkeypatch.setattr(placementos.services.operations, "OIDC_ADAPTER_IMPLEMENTED", False)
    monkeypatch.setattr(placementos.services.operations, "CLAMAV_ADAPTER_IMPLEMENTED", False)
    config = Settings(
        _env_file=None,
        IDENTITY_MODE="oidc",
        OIDC_ISSUER_URL="https://identity.apex.edu",
        OIDC_CLIENT_ID="placementos",
        OIDC_MEMBERSHIP_OWNER="identity@apex.edu",
        MALWARE_SCANNER_MODE="clamav",
    )
    snapshot = pilot_readiness_snapshot(config)
    assert "oidc_identity" in snapshot["blockers"]
    assert "real_malware_scanner" in snapshot["blockers"]
    checks = {item["key"]: item for item in snapshot["checks"]}
    assert checks["oidc_identity"]["classification"] == "implementation_required"
    assert checks["real_malware_scanner"]["classification"] == "implementation_required"


def test_implemented_production_adapters_clear_implementation_blockers():
    """When OIDC and ClamAV adapters are implemented (P19), they clear implementation blockers."""
    config = Settings(
        _env_file=None,
        IDENTITY_MODE="oidc",
        OIDC_ISSUER_URL="https://identity.apex.edu",
        OIDC_CLIENT_ID="placementos",
        OIDC_MEMBERSHIP_OWNER="identity@apex.edu",
        MALWARE_SCANNER_MODE="clamav",
    )
    snapshot = pilot_readiness_snapshot(config)
    assert "oidc_identity" not in snapshot["blockers"]
    assert "real_malware_scanner" not in snapshot["blockers"]
    checks = {item["key"]: item for item in snapshot["checks"]}
    assert checks["oidc_identity"]["classification"] == "configured"
    assert checks["real_malware_scanner"]["classification"] == "configured"
