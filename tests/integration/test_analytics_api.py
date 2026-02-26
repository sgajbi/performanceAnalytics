from fastapi.testclient import TestClient

from main import app


def test_positions_analytics_success(monkeypatch):
    client = TestClient(app)

    async def _mock_get_positions_analytics(self, portfolio_id, as_of_date, sections, performance_periods):  # noqa: ARG001
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
        "app.api.endpoints.analytics.PasInputService.get_positions_analytics",
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

    async def _mock_get_positions_analytics(self, portfolio_id, as_of_date, sections, performance_periods):  # noqa: ARG001
        return (200, {"portfolioId": "P1"})

    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasInputService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    response = client.post(
        "/analytics/positions",
        json={"portfolioId": "P1", "asOfDate": "2026-02-24"},
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

    response = client.post("/analytics/positions", json={"portfolioId": "P1", "asOfDate": "2026-02-24"})
    assert response.status_code == 503


def test_workbench_analytics_success():
    client = TestClient(app)
    response = client.post(
        "/analytics/workbench",
        json={
            "portfolioId": "P1",
            "asOfDate": "2026-02-24",
            "period": "YTD",
            "groupBy": "ASSET_CLASS",
            "benchmarkCode": "MODEL_60_40",
            "portfolioReturnPct": 4.2,
            "currentPositions": [
                {
                    "securityId": "AAPL.US",
                    "instrumentName": "Apple Inc",
                    "assetClass": "EQUITY",
                    "quantity": 120.0,
                },
                {
                    "securityId": "UST10Y",
                    "instrumentName": "US Treasury 10Y",
                    "assetClass": "FIXED_INCOME",
                    "quantity": 80.0,
                },
            ],
            "projectedPositions": [
                {
                    "securityId": "AAPL.US",
                    "instrumentName": "Apple Inc",
                    "assetClass": "EQUITY",
                    "baselineQuantity": 120.0,
                    "proposedQuantity": 100.0,
                    "deltaQuantity": -20.0,
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_mode"] == "pa_calc"
    assert body["portfolioId"] == "P1"
    assert len(body["allocationBuckets"]) >= 1
    assert "riskProxy" not in body
    assert body["activeReturnPct"] is not None


def test_workbench_analytics_security_group_uses_security_bucket_keys():
    client = TestClient(app)
    response = client.post(
        "/analytics/workbench",
        json={
            "portfolioId": "P1",
            "asOfDate": "2026-02-24",
            "period": "YTD",
            "groupBy": "SECURITY",
            "benchmarkCode": "CUSTOM",
            "currentPositions": [
                {
                    "securityId": "MSFT.US",
                    "instrumentName": "Microsoft",
                    "assetClass": "EQUITY",
                    "quantity": 50.0,
                }
            ],
            "projectedPositions": [],
        },
    )
    assert response.status_code == 200
    bucket = response.json()["allocationBuckets"][0]
    assert bucket["bucketKey"] == "MSFT.US"
    assert bucket["bucketLabel"] == "Microsoft"
