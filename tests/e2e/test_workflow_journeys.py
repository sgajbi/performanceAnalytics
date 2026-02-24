from fastapi.testclient import TestClient

from main import app


def test_e2e_platform_readiness_and_capabilities_contract() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/health/ready")
        capabilities = client.get("/integration/capabilities?consumerSystem=BFF&tenantId=default")

    assert health.status_code == 200
    assert ready.status_code == 200
    assert capabilities.status_code == 200

    body = capabilities.json()
    assert body["contractVersion"] == "v1"
    assert body["sourceService"] == "performance-analytics"
    assert "pas_ref" in body["supportedInputModes"]
    assert "inline_bundle" in body["supportedInputModes"]


def test_e2e_performance_twr_and_mwr_workflow() -> None:
    twr_payload = {
        "portfolio_number": "E2E_WORKFLOW_001",
        "performance_start_date": "2025-01-01",
        "report_end_date": "2025-01-03",
        "analyses": [{"period": "ITD", "frequencies": ["daily"]}],
        "metric_basis": "NET",
        "valuation_points": [
            {"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000.0, "end_mv": 1010.0},
            {"day": 2, "perf_date": "2025-01-02", "begin_mv": 1010.0, "end_mv": 1020.1},
            {"day": 3, "perf_date": "2025-01-03", "begin_mv": 1020.1, "end_mv": 1030.301},
        ],
    }
    mwr_payload = {
        "portfolio_number": "E2E_WORKFLOW_001",
        "begin_mv": 1000.0,
        "end_mv": 1030.301,
        "cash_flows": [],
        "as_of": "2025-01-03",
    }

    with TestClient(app) as client:
        twr_response = client.post("/performance/twr", json=twr_payload)
        mwr_response = client.post("/performance/mwr", json=mwr_payload)

    assert twr_response.status_code == 200
    assert mwr_response.status_code == 200

    twr_body = twr_response.json()
    assert "ITD" in twr_body["results_by_period"]
    assert twr_body["results_by_period"]["ITD"]["portfolio_return"]["base"] > 0

    mwr_body = mwr_response.json()
    assert mwr_body["portfolio_number"] == "E2E_WORKFLOW_001"


def test_e2e_contribution_attribution_and_lineage() -> None:
    contribution_payload = {
        "portfolio_number": "E2E_CONTRIB_001",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-01",
        "analyses": [{"period": "ITD", "frequencies": ["daily"]}],
        "portfolio_data": {
            "metric_basis": "NET",
            "valuation_points": [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1015}],
        },
        "positions_data": [
            {
                "position_id": "AAPL",
                "valuation_points": [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1015}],
            }
        ],
        "emit": {"timeseries": True},
    }
    attribution_payload = {
        "portfolio_number": "E2E_ATTRIB_001",
        "mode": "by_group",
        "group_by": ["sector"],
        "linking": "none",
        "frequency": "daily",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-01",
        "analyses": [{"period": "ITD", "frequencies": ["daily"]}],
        "portfolio_groups_data": [
            {
                "key": {"sector": "Tech"},
                "observations": [{"date": "2025-01-01", "return_base": 0.015, "weight_bop": 1.0}],
            }
        ],
        "benchmark_groups_data": [
            {
                "key": {"sector": "Tech"},
                "observations": [{"date": "2025-01-01", "return_base": 0.01, "weight_bop": 1.0}],
            }
        ],
    }

    with TestClient(app) as client:
        contribution_response = client.post("/performance/contribution", json=contribution_payload)
        attribution_response = client.post("/performance/attribution", json=attribution_payload)

        contribution_lineage = client.get(f"/performance/lineage/{contribution_response.json()['calculation_id']}")
        attribution_lineage = client.get(f"/performance/lineage/{attribution_response.json()['calculation_id']}")

    assert contribution_response.status_code == 200
    assert attribution_response.status_code == 200
    assert contribution_lineage.status_code == 200
    assert attribution_lineage.status_code == 200


def test_e2e_workbench_analytics_projection_view() -> None:
    payload = {
        "portfolioId": "P1",
        "asOfDate": "2026-02-24",
        "period": "YTD",
        "groupBy": "ASSET_CLASS",
        "benchmarkCode": "MODEL_60_40",
        "portfolioReturnPct": 4.2,
        "currentPositions": [
            {"securityId": "AAPL.US", "instrumentName": "Apple", "assetClass": "EQUITY", "quantity": 120.0},
            {"securityId": "UST10Y", "instrumentName": "UST 10Y", "assetClass": "FIXED_INCOME", "quantity": 80.0},
        ],
        "projectedPositions": [
            {
                "securityId": "AAPL.US",
                "instrumentName": "Apple",
                "assetClass": "EQUITY",
                "baselineQuantity": 120.0,
                "proposedQuantity": 100.0,
                "deltaQuantity": -20.0,
            }
        ],
    }

    with TestClient(app) as client:
        response = client.post("/analytics/workbench", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["portfolioId"] == "P1"
    assert body["source_mode"] == "pa_calc"
    assert len(body["allocationBuckets"]) >= 1


def test_e2e_pas_connected_modes(monkeypatch) -> None:
    async def _mock_get_performance_input(self, portfolio_id, as_of_date, lookback_days, consumer_system):  # noqa: ARG001
        return (
            200,
            {
                "contractVersion": "v1",
                "consumerSystem": "BFF",
                "portfolioId": portfolio_id,
                "performanceStartDate": "2026-01-01",
                "valuationPoints": [
                    {"day": 1, "perf_date": "2026-02-01", "begin_mv": 100.0, "end_mv": 101.0},
                    {"day": 2, "perf_date": "2026-02-23", "begin_mv": 101.0, "end_mv": 102.0},
                ],
            },
        )

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
        "app.api.endpoints.performance.PasSnapshotService.get_performance_input",
        _mock_get_performance_input,
    )
    monkeypatch.setattr(
        "app.api.endpoints.analytics.PasSnapshotService.get_positions_analytics",
        _mock_get_positions_analytics,
    )

    twr_pas_payload = {"portfolioId": "PORT-1001", "asOfDate": "2026-02-23", "periods": ["YTD"]}
    positions_payload = {
        "portfolioId": "PORT-1001",
        "asOfDate": "2026-02-23",
        "sections": ["BASE", "VALUATION"],
        "performancePeriods": ["YTD"],
    }

    with TestClient(app) as client:
        twr_pas_response = client.post("/performance/twr/pas-input", json=twr_pas_payload)
        positions_response = client.post("/analytics/positions", json=positions_payload)

    assert twr_pas_response.status_code == 200
    assert positions_response.status_code == 200
    assert twr_pas_response.json()["source_mode"] == "pas_ref"
    assert positions_response.json()["portfolioId"] == "PORT-1001"
