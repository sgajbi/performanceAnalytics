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
    
    assert response_data["reconciliation"]["total_active_return"] == pytest.approx(0.1)
    assert tech_group["selection"] == pytest.approx(0.25)


def test_attribution_endpoint_hierarchical(client):
    """
    Tests multi-level hierarchical attribution, ensuring bottom-up aggregation is correct.
    """
    payload = {
        "portfolio_number": "HIERARCHY_01", "mode": "by_instrument", "groupBy": ["assetClass", "sector"], "linking": "none", "frequency": "daily",
        "portfolio_data": {"report_start_date": "2025-01-01", "report_end_date": "2025-01-01", "metric_basis": "NET", "period_type": "YTD", "daily_data": [
            {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1020}
        ]},
        "instruments_data": [
            {"instrument_id": "AAPL", "meta": {"assetClass": "Equity", "sector": "Tech"}, "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 400, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 408}]},
            {"instrument_id": "JNJ", "meta": {"assetClass": "Equity", "sector": "Health"}, "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 300, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 303}]},
            {"instrument_id": "UST", "meta": {"assetClass": "Bond", "sector": "Government"}, "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 300, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 309}]}
        ],
        "benchmark_groups_data": [
            {"key": {"assetClass": "Equity", "sector": "Tech"}, "observations": [{"date": "2025-01-01", "return": 0.01, "weight_bop": 0.4}]},
            {"key": {"assetClass": "Equity", "sector": "Health"}, "observations": [{"date": "2025-01-01", "return": 0.01, "weight_bop": 0.3}]},
            {"key": {"assetClass": "Bond", "sector": "Government"}, "observations": [{"date": "2025-01-01", "return": 0.02, "weight_bop": 0.3}]}
        ]
    }
    response = client.post("/performance/attribution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["levels"]) == 2
    
    level_ac = data["levels"][0]
    level_sector = data["levels"][1]
    
    assert level_ac["dimension"] == "assetClass"
    assert level_sector["dimension"] == "assetClass -> sector"
    
    equity_ac_effects = next(g for g in level_ac["groups"] if g["key"]["assetClass"] == "Equity")
    tech_sector_effects = next(g for g in level_sector["groups"] if g["key"]["sector"] == "Tech")
    health_sector_effects = next(g for g in level_sector["groups"] if g["key"]["sector"] == "Health")

    # Assert bottom-up aggregation: Equity effects should equal sum of Tech + Health effects
    assert equity_ac_effects["allocation"] == pytest.approx(tech_sector_effects["allocation"] + health_sector_effects["allocation"])
    assert equity_ac_effects["selection"] == pytest.approx(tech_sector_effects["selection"] + health_sector_effects["selection"])
    assert equity_ac_effects["interaction"] == pytest.approx(tech_sector_effects["interaction"] + health_sector_effects["interaction"])


@pytest.mark.parametrize(
    "error_class, expected_status",
    [
        (InvalidEngineInputError, 400),
        (EngineCalculationError, 500),
        (ValueError, 400),
        (NotImplementedError, 400),
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