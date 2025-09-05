# tests/integration/test_contribution_api.py
from fastapi.testclient import TestClient
import pytest
from main import app

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
            "period_type": "ITD", # Add required fields
            "metric_basis": "NET", # Add required fields
            "daily_data": [
                { "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "End Market Value": 1020, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0},
                { "Perf. Date": "2025-01-02", "Begin Market Value": 1020, "End Market Value": 1080, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0}
            ]
        },
        "positions_data": [
            {
                "position_id": "Stock_A",
                "daily_data": [
                    { "Perf. Date": "2025-01-01", "Begin Market Value": 600, "End Market Value": 612, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0},
                    { "Perf. Date": "2025-01-02", "Begin Market Value": 612, "End Market Value": 670, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0}
                ]
            },
            {
                "position_id": "Stock_B",
                "daily_data": [
                    { "Perf. Date": "2025-01-01", "Begin Market Value": 400, "End Market Value": 408, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0},
                    { "Perf. Date": "2025-01-02", "Begin Market Value": 408, "End Market Value": 410, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0}
                ]
            }
        ]
    }

    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "CONTRIB_TEST_01"
    
    # Assert calculated values
    assert response_data["total_portfolio_return"] == pytest.approx(0.0295327)
    assert response_data["total_contribution"] == pytest.approx(0.02916085)
    
    contributions = {pc["position_id"]: pc for pc in response_data["position_contributions"]}
    assert contributions["Stock_A"]["total_contribution"] == pytest.approx(0.01936357)
    assert contributions["Stock_B"]["total_contribution"] == pytest.approx(0.00979728)