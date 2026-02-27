import json

import pytest

from app.enterprise_readiness import (
    _required_capability,
    authorize_write_request,
    validate_enterprise_runtime_config,
)


def test_validate_enterprise_runtime_config_raises_when_enforcement_enabled(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_POLICY_VERSION", " ")
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "120")
    monkeypatch.setenv("ENTERPRISE_ENFORCE_RUNTIME_CONFIG", "true")

    with pytest.raises(RuntimeError, match="enterprise_runtime_config_invalid"):
        validate_enterprise_runtime_config()


def test_required_capability_returns_none_when_no_matching_rule(monkeypatch):
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps({"POST /analytics": "analytics.write"}),
    )
    assert _required_capability("POST", "/different/path") is None


def test_authorize_write_request_allows_when_no_capability_rule_matches(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    monkeypatch.setenv(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        json.dumps({"POST /analytics": "analytics.write"}),
    )
    headers = {
        "X-Actor-Id": "a1",
        "X-Tenant-Id": "t1",
        "X-Role": "analyst",
        "X-Correlation-Id": "c1",
        "X-Service-Identity": "pa",
    }
    allowed, reason = authorize_write_request("POST", "/reports/run", headers)
    assert allowed is True
    assert reason is None
