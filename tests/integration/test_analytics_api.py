from fastapi.testclient import TestClient

from main import app


def test_positions_analytics_success(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(self, portfolio_id, as_of_date, sections, performance_periods):  # noqa: ARG001
        return (
            200,
            {
                "portfolio_id": portfolio_id,
                "as_of_date": str(as_of_date),
                "total_market_value": 1000.0,
                "positions": [{"securityId": "EQ_1", "quantity": 10}],
            },
        )

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasInputService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post(
        "/analytics/positions",
        json={
            "portfolio_id": "P1",
            "as_of_date": "2026-02-24",
            "sections": ["BASE", "VALUATION", "PERFORMANCE"],
            "performancePeriods": ["YTD"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_id"] == "P1"
    assert body["total_market_value"] == 1000.0
    assert len(body["positions"]) == 1


def test_positions_analytics_invalid_payload(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(self, portfolio_id, as_of_date, sections, performance_periods):  # noqa: ARG001
        return (200, {"portfolio_id": "P1"})

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasInputService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post(
        "/analytics/positions",
        json={"portfolio_id": "P1", "as_of_date": "2026-02-24"},
    )
    assert response.status_code == 502


def test_positions_analytics_upstream_error_passthrough(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(self, portfolio_id, as_of_date, sections, performance_periods):  # noqa: ARG001
        return (503, {"detail": "pas unavailable"})

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasInputService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post("/analytics/positions", json={"portfolio_id": "P1", "as_of_date": "2026-02-24"})
    assert response.status_code == 503


def test_workbench_analytics_endpoint_removed():
    client = TestClient(app)
    response = client.post("/analytics/workbench", json={})
    assert response.status_code == 404
