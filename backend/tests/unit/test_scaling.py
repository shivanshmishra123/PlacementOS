"""Unit coverage for P13 conservative operating-policy defaults."""

import uuid

import pytest
from pydantic import ValidationError

from placementos.schemas.scaling import OperatingPolicyRevisionCreate
from placementos.services.scaling import default_policy


def test_default_policy_is_explicit_and_conservative():
    institution_id = uuid.uuid4()
    policy = default_policy(institution_id)
    assert policy.institution_id == institution_id
    assert policy.revision_number == 0
    assert policy.source == "system_default"
    assert policy.onboarding_status == "configuration_pending"
    assert policy.max_open_drives == 1_000
    assert policy.max_students_per_import == 10_000
    assert policy.max_export_rows == 10_000


def test_operating_policy_rejects_zero_quota():
    with pytest.raises(ValidationError):
        OperatingPolicyRevisionCreate(
            expected_revision=0,
            onboarding_status="synthetic_ready",
            max_open_drives=0,
            max_students_per_import=10,
            max_export_rows=10,
            change_reason="Invalid zero quota fixture",
        )
