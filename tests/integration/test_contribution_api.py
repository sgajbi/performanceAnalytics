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


@pytest.fixture(scope="module")
def happy_path_payload():
    """Provides a standard, valid payload for contribution tests."""
    return {
        "portfolio_number": "CONTRIB_TEST_01",
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-02",
            "period_type": "ITD",
            "metric_basis": "NET",
            "daily_data": [
                {"Perf. Date": "2025-01-01", "Begin Market Value": 1000, "End Market Value": 1020, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 1},
                {"Perf. Date": "2025-01-02", "Begin Market Value": 1020, "End Market Value": 1080, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 2},
            ],
        },
        "positions_data": [
            {
                "position_id": "Stock_A",
                "meta": {"sector": "Technology"},
                "daily_data": [
                    {"Perf. Date": "2025-01-01", "Begin Market Value": 600, "End Market Value": 612, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 1},
                    {"Perf. Date": "2025-01-02", "Begin Market Value": 612, "End Market Value": 670, "BOD Cashflow": 50, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 2},
                ],
            }
        ],
    }


def test_contribution_endpoint_happy_path_and_envelope(client, happy_path_payload):
    """
    Tests the /performance/contribution endpoint with a valid payload
    and verifies the shared response envelope is present and correct.
    """
    response = client.post("/performance/contribution", json=happy_path_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "CONTRIB_TEST_01"
    assert "total_contribution" in response_data
    assert len(response_data["position_contributions"]) == 1
    assert response_data["position_contributions"][0]["position_id"] == "Stock_A"

    assert "meta" in response_data
    assert response_data["meta"]["engine_version"] is not None
    assert response_data["meta"]["precision_mode"] == "FLOAT64"

    assert "diagnostics" in response_data
    assert response_data["diagnostics"]["nip_days"] == 0

    assert "audit" in response_data
    assert response_data["audit"]["counts"]["input_positions"] == 1
    assert response_data["audit"]["counts"]["calculation_days"] == 2


def test_contribution_endpoint_no_smoothing(client, happy_path_payload):
    """
    Tests that the endpoint correctly processes a request with smoothing disabled
    and the results do not reconcile with the geometric portfolio return.
    """
    payload = happy_path_payload.copy()
    payload["smoothing"] = {"method": "NONE"}

    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 200
    response_data = response.json()

    assert response_data["total_contribution"] != pytest.approx(response_data["total_portfolio_return"])
    assert response_data["position_contributions"][0]["total_contribution"] == pytest.approx(1.94766, abs=1e-5)


def test_contribution_endpoint_with_timeseries(client, happy_path_payload):
    """
    Tests that the endpoint correctly returns time-series data when requested.
    """
    payload = happy_path_payload.copy()
    payload["emit"] = {"timeseries": True, "by_position_timeseries": True}

    response = client.post("/performance/contribution", json=payload)
    assert response.status_code == 200
    response_data = response.json()

    assert "timeseries" in response_data
    assert len(response_data["timeseries"]) == 2
    assert response_data["timeseries"][0]["date"] == "2025-01-01"

    assert "by_position_timeseries" in response_data
    assert len(response_data["by_position_timeseries"]) == 1
    assert response_data["by_position_timeseries"][0]["position_id"] == "Stock_A"
    assert len(response_data["by_position_timeseries"][0]["series"]) == 2


def test_contribution_endpoint_hierarchy_returns_placeholder(client, happy_path_payload):
    """
    Tests that a request with the 'hierarchy' field returns a 200 OK
    with a valid but empty placeholder structure.
    """
    payload = happy_path_payload.copy()
    payload["hierarchy"] = ["assetClass", "sector"]

    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] is not None
    assert data["summary"]["portfolio_contribution"] == 0.0
    assert data["levels"] == []
    assert data["position_contributions"] is None # Should not be populated for hierarchical


def test_contribution_endpoint_error_handling(client, mocker):
    """Tests that a generic server error is raised for calculation failures."""
    mocker.patch("app.api.endpoints.contribution.calculate_position_contribution", side_effect=EngineCalculationError("Test Error"))

    payload = {
        "portfolio_number": "ERROR",
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-02",
            "period_type": "ITD",
            "metric_basis": "NET",
            "daily_data": [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1025}],
        },
        "positions_data": [],
    }
    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 500
    assert "An unexpected error occurred" in response.json()["detail"]