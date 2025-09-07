# tests/integration/test_performance_api.py
import json
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from main import app
from engine.exceptions import EngineCalculationError, InvalidEngineInputError


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


def test_calculate_twr_endpoint_happy_path_and_diagnostics(client):
    """
    Tests the /performance/twr endpoint (happy path) and verifies the
    new shared response footer is correctly populated.
    """
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputStandardGrowth.json")

    input_data["calculation_id"] = str(uuid4())
    input_data["rounding_precision"] = 6
    input_data["frequencies"] = ["daily", "monthly"]

    response = client.post("/performance/twr", json=input_data)

    assert response.status_code == 200

    response_data = response.json()
    assert "calculation_id" in response_data
    assert "breakdowns" in response_data

    assert "meta" in response_data
    assert response_data["meta"]["engine_version"] is not None
    assert response_data["meta"]["precision_mode"] == "FLOAT64"

    assert "diagnostics" in response_data
    assert response_data["diagnostics"]["nip_days"] == 0
    assert response_data["diagnostics"]["reset_days"] == 0

    assert "audit" in response_data
    assert response_data["audit"]["counts"]["input_rows"] == 5


def test_calculate_twr_endpoint_decimal_strict_mode(client):
    """
    Tests that setting precision_mode to DECIMAL_STRICT is respected
    and reflected in the response metadata.
    """
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInput.json")

    input_data["calculation_id"] = str(uuid4())
    input_data["frequencies"] = ["daily"]
    input_data["precision_mode"] = "DECIMAL_STRICT"

    response = client.post("/performance/twr", json=input_data)
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["meta"]["precision_mode"] == "DECIMAL_STRICT"
    # FIX: The test should check for the new, default field name.
    daily_ror = response_data["breakdowns"]["daily"][2]["summary"]["period_return_pct"]
    assert Decimal(str(daily_ror)) == pytest.approx(Decimal("0.4558139535"))


def test_calculate_twr_endpoint_quarterly_weekly_annualized(client):
    """
    Tests quarterly and weekly breakdowns with annualization enabled to ensure
    all paths in the breakdown module are covered.
    """
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputlong.json")

    input_data["calculation_id"] = str(uuid4())
    input_data["frequencies"] = ["quarterly", "weekly"]
    input_data["annualization"] = {"enabled": True, "basis": "BUS/252"}

    response = client.post("/performance/twr", json=input_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "quarterly" in response_data["breakdowns"]
    assert "weekly" in response_data["breakdowns"]

    quarter_1 = response_data["breakdowns"]["quarterly"][0]
    assert quarter_1["period"] == "2024-Q1"
    assert "annualized_return_pct" in quarter_1["summary"]
    assert quarter_1["summary"]["annualized_return_pct"] is not None

    week_1 = response_data["breakdowns"]["weekly"][0]
    assert "annualized_return_pct" in week_1["summary"]


def test_calculate_twr_with_empty_period(client):
    """
    Tests that the breakdown aggregator correctly handles periods with no data.
    """
    payload = {
        "portfolio_number": "EMPTY_PERIOD_TEST",
        "performance_start_date": "2024-12-31",
        "report_end_date": "2025-03-31",
        "metric_basis": "NET",
        "period_type": "YTD",
        "frequencies": ["monthly"],
        "daily_data": [
            {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1010},
            # February is intentionally left empty
            {"Day": 2, "Perf. Date": "2025-03-01", "Begin Market Value": 1010, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1020}
        ]
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()
    monthly_breakdown = data["breakdowns"]["monthly"]

    # The response should only contain breakdowns for Jan and Mar, skipping empty Feb
    assert len(monthly_breakdown) == 2
    assert monthly_breakdown[0]["period"] == "2025-01"
    assert monthly_breakdown[1]["period"] == "2025-03"


@pytest.mark.parametrize(
    "error_class, expected_status",
    [
        (InvalidEngineInputError, 400),
        (EngineCalculationError, 500),
        (Exception, 500)
    ]
)
def test_calculate_twr_endpoint_error_handling(client, mocker, error_class, expected_status):
    """Tests that the TWR endpoint correctly handles engine exceptions."""
    mocker.patch('app.api.endpoints.performance.run_calculations', side_effect=error_class("Test Error"))

    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInput.json")
    input_data["frequencies"] = ["daily"]

    response = client.post("/performance/twr", json=input_data)

    assert response.status_code == expected_status
    assert "detail" in response.json()