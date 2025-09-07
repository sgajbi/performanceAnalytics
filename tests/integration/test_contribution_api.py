# tests/integration/test_contribution_api.py
from fastapi.testclient import TestClient
import pytest
from main import app
from engine.exceptions import EngineCalculationError


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_contribution_endpoint_happy_path_and_envelope(client, happy_path_payload):
    """Tests the /performance/contribution endpoint and verifies the shared response envelope."""
    response = client.post("/performance/contribution", json=happy_path_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_number"] == "CONTRIB_TEST_01"
    assert "total_contribution" in response_data
    assert len(response_data["position_contributions"]) == 1
    assert response_data["position_contributions"][0]["position_id"] == "Stock_A"

    assert "meta" in response_data
    assert response_data["meta"]["engine_version"] is not None
    assert "diagnostics" in response_data
    assert response_data["diagnostics"]["nip_days"] == 0
    assert "audit" in response_data
    assert response_data["audit"]["counts"]["input_positions"] == 1
    assert response_data["audit"]["counts"]["calculation_days"] == 2


def test_contribution_endpoint_no_smoothing(client, happy_path_payload):
    """Tests that the endpoint correctly processes a request with smoothing disabled."""
    payload = happy_path_payload.copy()
    payload["smoothing"] = {"method": "NONE"}

    response = client.post("/performance/contribution", json=payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total_contribution"] != pytest.approx(response_data["total_portfolio_return"])
    assert response_data["position_contributions"][0]["total_contribution"] == pytest.approx(1.94766, abs=1e-5)


def test_contribution_endpoint_with_timeseries(client, happy_path_payload):
    """Tests that the endpoint correctly returns time-series data when requested."""
    payload = happy_path_payload.copy()
    payload["emit"] = {"timeseries": True, "by_position_timeseries": True}

    response = client.post("/performance/contribution", json=payload)
    assert response.status_code == 200
    response_data = response.json()

    assert "timeseries" in response_data
    assert len(response_data["timeseries"]) == 2
    assert "by_position_timeseries" in response_data
    assert len(response_data["by_position_timeseries"]) == 1
    assert len(response_data["by_position_timeseries"][0]["series"]) == 2


def test_contribution_endpoint_hierarchy_happy_path(client, happy_path_payload):
    """Tests a hierarchical contribution request aggregates correctly."""
    payload = happy_path_payload.copy()
    payload["hierarchy"] = ["sector", "position_id"]
    payload["positions_data"].append(
        {
            "position_id": "Stock_B",
            "meta": {"sector": "Technology"},
            "daily_data": [
                {"day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 408},
                {"day": 2, "perf_date": "2025-01-02", "begin_mv": 408, "end_mv": 410},
            ],
        }
    )

    response = client.post("/performance/contribution", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "summary" in data
    assert data["summary"]["portfolio_contribution"] == pytest.approx(2.95327, abs=1e-5)
    assert len(data["levels"]) == 2
    sector_level = data["levels"][0]
    position_level = data["levels"][1]
    assert len(sector_level["rows"]) == 1
    assert len(position_level["rows"]) == 2
    stock_a_row = next(r for r in position_level["rows"] if r["key"]["position_id"] == "Stock_A")
    stock_b_row = next(r for r in position_level["rows"] if r["key"]["position_id"] == "Stock_B")
    assert stock_a_row["contribution"] + stock_b_row["contribution"] == pytest.approx(sector_level["rows"][0]["contribution"])


def test_contribution_endpoint_error_handling(client, mocker):
    """Tests that a generic server error is raised for calculation failures."""
    mocker.patch("app.api.endpoints.contribution.calculate_position_contribution", side_effect=EngineCalculationError("Test Error"))
    payload = {
        "portfolio_number": "ERROR",
        "portfolio_data": {
            "report_start_date": "2025-01-01", "report_end_date": "2025-01-02",
            "period_type": "ITD", "metric_basis": "NET",
            "daily_data": [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1025}],
        },
        "positions_data": [],
    }
    response = client.post("/performance/contribution", json=payload)
    assert response.status_code == 500
    assert "An unexpected error occurred" in response.json()["detail"]