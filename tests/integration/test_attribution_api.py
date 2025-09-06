# tests/integration/test_attribution_api.py
from fastapi.testclient import TestClient
import pytest
from main import app
from engine.exceptions import EngineCalculationError, InvalidEngineInputError


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c


def test_attribution_endpoint_by_instrument_happy_path(client):
    """
    Tests the /performance/attribution endpoint end-to-end with a valid
    'by_instrument' payload, verifying the calculated results.
    """
    payload = {
        "portfolio_number": "ATTRIB_BY_INST_01", "mode": "by_instrument", "groupBy": ["sector"], "linking": "none", "frequency": "daily",
        "portfolio_data": {"report_start_date": "2025-01-01", "report_end_date": "2025-01-01", "metric_basis": "NET", "period_type": "YTD", "daily_data": [
            {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1018.5}
        ]},
        "instruments_data": [
            {"instrument_id": "AAPL", "meta": {"sector": "Tech"}, "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 600, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 612}]},
            {"instrument_id": "JNJ", "meta": {"sector": "Health"}, "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 400, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 406.5}]}
        ],
        "benchmark_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-01", "return": 0.015, "weight_bop": 0.5}]},
            {"key": {"sector": "Health"}, "observations": [{"date": "2025-01-01", "return": 0.02, "weight_bop": 0.5}]}
        ]
    }

    response = client.post("/performance/attribution", json=payload)
    assert response.status_code == 200
    response_data = response.json()
    
    assert response_data["portfolio_number"] == "ATTRIB_BY_INST_01"
    level = response_data["levels"][0]
    tech_group = next(g for g in level["groups"] if g["key"]["sector"] == "Tech")
    
    assert response_data["reconciliation"]["total_active_return"] == pytest.approx(0.001)
    assert tech_group["selection"] == pytest.approx(0.0025)


@pytest.mark.parametrize(
    "error_class, expected_status",
    [
        (InvalidEngineInputError, 400),
        (EngineCalculationError, 500),
        (ValueError, 400),
        (Exception, 500)
    ]
)
def test_attribution_endpoint_error_handling(client, mocker, error_class, expected_status):
    """Tests that the attribution endpoint correctly handles engine exceptions."""
    mocker.patch('app.api.endpoints.performance.run_attribution_calculations', side_effect=error_class("Test Error"))
    
    payload = {"portfolio_number": "ERROR", "mode": "by_group", "groupBy": ["sector"], "benchmark_groups_data": [], "linking": "none"}
    response = client.post("/performance/attribution", json=payload)
    
    assert response.status_code == expected_status
    assert "detail" in response.json()