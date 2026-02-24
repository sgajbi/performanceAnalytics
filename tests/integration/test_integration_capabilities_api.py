from fastapi.testclient import TestClient

from main import app


def test_integration_capabilities_default_contract():
    with TestClient(app) as client:
        response = client.get("/integration/capabilities?consumerSystem=BFF&tenantId=default")

    assert response.status_code == 200
    body = response.json()
    assert body["contractVersion"] == "v1"
    assert body["sourceService"] == "performance-analytics"
    assert body["consumerSystem"] == "BFF"
    assert body["tenantId"] == "default"
    assert body["supportedInputModes"] == ["pas_ref", "inline_bundle"]
    assert len(body["features"]) >= 6
    assert len(body["workflows"]) >= 3
    features = {item["key"] for item in body["features"]}
    assert "pa.analytics.risk" in features
    assert "pa.analytics.concentration" in features
    assert "pa.execution.stateful_pas_ref" in features
    assert "pa.execution.stateless_inline_bundle" in features
    assert response.headers.get("X-Correlation-Id")
    assert response.headers.get("X-Request-Id")
    assert response.headers.get("X-Trace-Id")


def test_integration_capabilities_env_override(monkeypatch):
    monkeypatch.setenv("PA_CAP_ATTRIBUTION_ENABLED", "false")
    monkeypatch.setenv("PA_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", "false")
    monkeypatch.setenv("PA_POLICY_VERSION", "tenant-a-v4")
    with TestClient(app) as client:
        response = client.get("/integration/capabilities?consumerSystem=DPM&tenantId=tenant-a")

    assert response.status_code == 200
    body = response.json()
    assert body["consumerSystem"] == "DPM"
    assert body["tenantId"] == "tenant-a"
    assert body["policyVersion"] == "tenant-a-v4"
    features = {item["key"]: item["enabled"] for item in body["features"]}
    assert features["pa.analytics.attribution"] is False
    assert body["supportedInputModes"] == ["pas_ref"]


def test_health_and_metrics_endpoints_available():
    with TestClient(app) as client:
        health = client.get("/health")
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        metrics = client.get("/metrics")

    assert health.status_code == 200
    assert live.status_code == 200
    assert ready.status_code == 200
    assert health.json() == {"status": "ok"}
    assert live.json() == {"status": "live"}
    assert ready.json() == {"status": "ready"}
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text or "http_request_duration" in metrics.text
