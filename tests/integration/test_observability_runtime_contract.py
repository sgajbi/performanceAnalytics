import logging

from fastapi.testclient import TestClient

from main import app


def test_health_request_emits_duration_log_and_propagates_correlation_headers(caplog):
    with caplog.at_level(logging.INFO, logger="http.access"):
        with TestClient(app) as client:
            response = client.get("/health", headers={"X-Correlation-Id": "corr-runtime-1"})

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-Id") == "corr-runtime-1"
    assert response.headers.get("X-Request-Id")
    assert response.headers.get("X-Trace-Id")

    matching = [
        record
        for record in caplog.records
        if record.name == "http.access" and record.getMessage() == "request.completed"
    ]
    assert matching
    fields = getattr(matching[-1], "extra_fields", {})
    assert fields["endpoint"] == "/health"
    assert fields["http_method"] == "GET"
    assert fields["duration_ms"] >= 0
