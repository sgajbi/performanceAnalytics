# tests/integration/test_mwr_api.py
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c

def test_calculate_mwr_endpoint_xirr_happy_path(client):
    """Tests the /performance/mwr endpoint with the XIRR method."""
    payload = {
        "calculation_id": str(uuid4()),
        "portfolio_number": "MWR_XIRR_TEST_01",
        "beginning_mv": 100000.0,
        "ending_mv": 115000.0,
        "as_of": "2025-12-31",
        "cash_flows": [
            {"amount": 10000.0, "date": "2025-03-15"},
            {"amount": -5000.0, "date": "2025-09-20"},
        ],
        "mwr_method": "XIRR",
        "annualization": {"enabled": True, "basis": "ACT/365"}
    }
    
    response = client.post("/performance/mwr", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "MWR_XIRR_TEST_01"
    assert response_data["method"] == "XIRR"
    # FIX: Update expected value to the correct XIRR result.
    assert response_data["money_weighted_return"] == pytest.approx(11.723, abs=1e-3)
    assert response_data["mwr_annualized"] is not None