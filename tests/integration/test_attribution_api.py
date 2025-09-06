# tests/integration/test_attribution_api.py
from fastapi.testclient import TestClient
import pytest
from main import app


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c


def test_attribution_endpoint_happy_path(client):
    """
    Tests the /performance/attribution endpoint with a valid 'by_instrument'
    payload. This initial test verifies the endpoint is wired correctly
    and returns a valid response structure from the placeholder logic.
    """
    payload = {
        "portfolio_number": "ATTRIB_INTEG_TEST_01",
        "mode": "by_instrument",
        "groupBy": ["assetClass", "sector"],
        "model": "BF",
        "linking": "carino",
        "frequency": "monthly",
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-31",
            "metric_basis": "NET",
            "period_type": "ITD",
            "daily_data": [
                {
                    "Day": 1,
                    "Perf. Date": "2025-01-01",
                    "Begin Market Value": 1000,
                    "BOD Cashflow": 0,
                    "Eod Cashflow": 0,
                    "Mgmt fees": 0,
                    "End Market Value": 1010
                }
            ]
        },
        "instruments_data": [],
        "benchmark_groups_data": []
    }

    response = client.post("/performance/attribution", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "ATTRIB_INTEG_TEST_01"
    assert response_data["model"] == "BF"
    assert "calculation_id" in response_data
    assert "levels" in response_data
    assert "reconciliation" in response_data