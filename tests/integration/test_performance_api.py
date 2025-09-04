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


def test_calculate_performance_happy_path(client):
    """
    Tests the /calculate_performance endpoint with a valid request (happy path).
    """
    # 1. Arrange
    # Load a known-good input file
    base_path = Path(__file__).parent.parent
    input_data = load_json_from_file(base_path / "sampleInputStandardGrowth.json")

    # 2. Act
    # Make a POST request to the endpoint
    response = client.post("/calculate_performance", json=input_data)

    # 3. Assert
    # Check for a successful HTTP status code
    assert response.status_code == 200

    # Check that the response body is valid JSON and contains expected keys
    response_data = response.json()
    assert isinstance(response_data, dict)
    assert "portfolio_number" in response_data
    assert "calculated_daily_performance" in response_data
    assert "summary_performance" in response_data
    assert len(response_data["calculated_daily_performance"]) > 0