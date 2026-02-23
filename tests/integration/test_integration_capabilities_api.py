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
    assert len(body["features"]) >= 4
    assert len(body["workflows"]) >= 2


def test_integration_capabilities_env_override(monkeypatch):
    monkeypatch.setenv("PA_CAP_ATTRIBUTION_ENABLED", "false")
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
