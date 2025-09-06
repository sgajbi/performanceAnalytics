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