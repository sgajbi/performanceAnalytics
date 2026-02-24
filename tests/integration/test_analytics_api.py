from fastapi.testclient import TestClient

from main import app


def test_positions_analytics_success(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(
        self, portfolio_id, as_of_date, sections, performance_periods
    ):  # noqa: ARG001
        return (
            200,
            {
                "portfolioId": portfolio_id,
                "asOfDate": str(as_of_date),
                "totalMarketValue": 1000.0,
                "positions": [{"securityId": "EQ_1", "quantity": 10}],
            },
        )

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasSnapshotService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post(
        "/analytics/positions",
        json={
            "portfolioId": "P1",
            "asOfDate": "2026-02-24",
            "sections": ["BASE", "VALUATION", "PERFORMANCE"],
            "performancePeriods": ["YTD"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["portfolioId"] == "P1"
    assert body["totalMarketValue"] == 1000.0
    assert len(body["positions"]) == 1


def test_positions_analytics_invalid_payload(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(
        self, portfolio_id, as_of_date, sections, performance_periods
    ):  # noqa: ARG001
        return (200, {"portfolioId": "P1"})

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasSnapshotService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post(
        "/analytics/positions",
        json={"portfolioId": "P1", "asOfDate": "2026-02-24"},
    )
    assert response.status_code == 502
