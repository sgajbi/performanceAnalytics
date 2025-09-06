# tests/integration/test_contribution_api.py
from fastapi.testclient import TestClient
import pytest
from main import app
from engine.exceptions import EngineCalculationError


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c

def test_contribution_endpoint_happy_path(client):
    """Tests the /performance/contribution endpoint with a valid payload."""
    payload = {
        "portfolio_number": "CONTRIB_TEST_01",
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-02",
            "period_type": "ITD",
            "metric_basis": "NET",
            "daily_data": [
                { "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "End Market Value": 1020, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 1},
                { "Perf. Date": "2025-01-02", "Begin Market Value": 1020, "End Market Value": 1080, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 2}
            ]
        },
        "positions_data": [
            {
                "position_id": "Stock_A",
                "daily_data": [
                    { "Perf. Date": "2025-01-01", "Begin Market Value": 600, "End Market Value": 612, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 1},
                    { "Perf. Date": "2025-01-02", "Begin Market Value": 612, "End Market Value": 670, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 2}
                ]
            }
        ]
    }

    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "CONTRIB_TEST_01"
    assert "total_contribution" in response_data
    assert len(response_data["position_contributions"]) == 1
    assert response_data["position_contributions"][0]["position_id"] == "Stock_A"


def test_contribution_endpoint_error_handling(client, mocker):
    """Tests that a generic server error is raised for calculation failures."""
    mocker.patch('engine.contribution.calculate_position_contribution', side_effect=EngineCalculationError("Test Error"))
    
    # A minimal payload is needed to trigger the endpoint
    payload = { "portfolio_number": "ERROR", "portfolio_data": {}, "positions_data": []}
    response = client.post("/performance/contribution", json=payload)
    
    assert response.status_code == 500
    assert "An unexpected error occurred" in response.json()["detail"]