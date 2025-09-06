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
    Tests the /performance/attribution endpoint end-to-end with a valid
    'by_group' payload, verifying the calculated results.
    """
    payload = {
        "portfolio_number": "ATTRIB_INTEG_TEST_01",
        "mode": "by_group",
        "groupBy": ["sector"],
        "model": "BF",
        "linking": "none",
        "frequency": "monthly",
        "portfolio_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-15", "return": 0.05, "weight_bop": 0.7}]},
            {"key": {"sector": "Health"}, "observations": [{"date": "2025-01-20", "return": 0.02, "weight_bop": 0.3}]}
        ],
        "benchmark_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-10", "return": 0.04, "weight_bop": 0.6}]},
            {"key": {"sector": "Health"}, "observations": [{"date": "2025-01-18", "return": 0.03, "weight_bop": 0.4}]}
        ]
    }

    response = client.post("/performance/attribution", json=payload)
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["portfolio_number"] == "ATTRIB_INTEG_TEST_01"
    level = response_data["levels"][0]
    assert len(level["groups"]) == 2
    
    health_group = next(g for g in level["groups"] if g["key"]["sector"] == "Health")
    tech_group = next(g for g in level["groups"] if g["key"]["sector"] == "Tech")

    # Rb_total = 0.6*0.04 + 0.4*0.03 = 0.036
    # Tech Alloc = (0.7 - 0.6) * (0.04 - 0.036) = 0.0004
    assert tech_group["allocation"] == pytest.approx(0.0004)
    # Health Select = 0.4 * (0.02 - 0.03) = -0.004
    assert health_group["selection"] == pytest.approx(-0.004)

    # Active Return = (0.7*0.05 + 0.3*0.02) - 0.036 = 0.041 - 0.036 = 0.005
    assert response_data["reconciliation"]["total_active_return"] == pytest.approx(0.005)
    assert level["totals"]["total_effect"] == pytest.approx(0.005)