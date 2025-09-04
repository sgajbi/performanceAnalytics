# tests/integration/test_performance_api.py
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the API tests."""
    with TestClient(app) as c:
        yield c


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


def test_calculate_twr_endpoint_happy_path(client):
    """
    Tests the /performance/twr endpoint with a valid request (happy path).
    """
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputStandardGrowth.json")

    input_data["calculation_id"] = str(uuid4())
    input_data["rounding_precision"] = 6
    input_data["frequencies"] = ["daily", "monthly"]

    response = client.post("/performance/twr", json=input_data)

    assert response.status_code == 200

    response_data = response.json()
    assert isinstance(response_data, dict)
    assert "calculation_id" in response_data
    
    assert "breakdowns" in response_data
    assert "daily" in response_data["breakdowns"]
    assert "monthly" in response_data["breakdowns"]
    assert len(response_data["breakdowns"]["daily"]) == 5
    assert len(response_data["breakdowns"]["monthly"]) == 1
    assert response_data["breakdowns"]["monthly"][0]["period"] == "2025-01"