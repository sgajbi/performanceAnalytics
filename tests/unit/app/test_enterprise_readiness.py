import json

from app.enterprise_readiness import (
    authorize_write_request,
    is_feature_enabled,
    redact_sensitive,
    validate_enterprise_runtime_config,
)


def test_feature_flags_resolution(monkeypatch):
    monkeypatch.setenv(
        "ENTERPRISE_FEATURE_FLAGS_JSON",
        json.dumps({"analytics.risk": {"tenant-x": {"analyst": True, "*": False}}}),
    )
    assert is_feature_enabled("analytics.risk", "tenant-x", "analyst") is True
    assert is_feature_enabled("analytics.risk", "tenant-x", "viewer") is False


def test_redaction_masks_sensitive_values():
    payload = {"token": "abc", "nested": [{"ssn": "123"}, {"safe": "ok"}]}
    redacted = redact_sensitive(payload)
    assert redacted["token"] == "***REDACTED***"
    assert redacted["nested"][0]["ssn"] == "***REDACTED***"
    assert redacted["nested"][1]["safe"] == "ok"


def test_authorize_write_request_enforces_required_headers_when_enabled(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_ENFORCE_AUTHZ", "true")
    allowed, reason = authorize_write_request("POST", "/analytics", {})
    assert allowed is False
    assert reason.startswith("missing_headers:")


def test_authorize_write_request_enforces_capability_rules(monkeypatch):
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
        "X-Capabilities": "analytics.read",
    }
    denied, denied_reason = authorize_write_request("POST", "/analytics/calc", headers)
    assert denied is False
    assert denied_reason == "missing_capability:analytics.write"

    headers["X-Capabilities"] = "analytics.read,analytics.write"
    allowed, allowed_reason = authorize_write_request("POST", "/analytics/calc", headers)
    assert allowed is True
    assert allowed_reason is None


def test_validate_enterprise_runtime_config_reports_rotation_issue(monkeypatch):
    monkeypatch.setenv("ENTERPRISE_SECRET_ROTATION_DAYS", "120")
    issues = validate_enterprise_runtime_config()
    assert "secret_rotation_days_out_of_range" in issues
