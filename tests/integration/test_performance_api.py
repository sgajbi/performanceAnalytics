# tests/integration/test_performance_api.py
import json
from pathlib import Path

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
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputStandardGrowth.json")

    # 2. Act
    # Make a POST request to the new endpoint path
    response = client.post("/performance/twr", json=input_data)

    # 3. Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, dict)
    assert "portfolio_number" in response_data
    assert "calculated_daily_performance" in response_data
    assert "summary_performance" in response_data
    assert len(response_data["calculated_daily_performance"]) > 0