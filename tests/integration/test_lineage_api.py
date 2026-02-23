# tests/integration/test_lineage_api.py
import os
import shutil
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from main import app

settings = get_settings()


@pytest.fixture(scope="module")
def client():
    # Clean up lineage directory before tests
    if os.path.exists(settings.LINEAGE_STORAGE_PATH):
        shutil.rmtree(settings.LINEAGE_STORAGE_PATH)
    os.makedirs(settings.LINEAGE_STORAGE_PATH)

    with TestClient(app) as c:
        yield c

    # Clean up after tests
    if os.path.exists(settings.LINEAGE_STORAGE_PATH):
        shutil.rmtree(settings.LINEAGE_STORAGE_PATH)


def test_lineage_end_to_end_flow(client):
    """Tests the full lineage flow: TWR calc -> lineage capture -> lineage retrieval."""
    twr_payload = {
        "portfolio_number": "LINEAGE_TEST",
        "performance_start_date": "2024-12-31",
        "metric_basis": "NET",
        "report_end_date": "2025-01-01",
        "analyses": [{"period": "YTD", "frequencies": ["daily"]}],
        "valuation_points": [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000.0, "end_mv": 1010.0}],
    }

    # 1. Run a calculation
    twr_response = client.post("/performance/twr", json=twr_payload)
    assert twr_response.status_code == 200
    twr_data = twr_response.json()
    calculation_id = twr_data["calculation_id"]

    # 2. Retrieve lineage data
    lineage_response = client.get(f"/performance/lineage/{calculation_id}")
    assert lineage_response.status_code == 200
    lineage_data = lineage_response.json()

    assert lineage_data["calculation_id"] == calculation_id
    assert lineage_data["calculation_type"] == "TWR"
    assert "Z" in lineage_data["timestamp_utc"]
    assert "request.json" in lineage_data["artifacts"]
    assert "response.json" in lineage_data["artifacts"]
    assert "twr_calculation_details.csv" in lineage_data["artifacts"]


def test_get_lineage_data_not_found(client):
    """Tests that a 404 is returned for a non-existent calculation_id."""
    non_existent_id = uuid4()
    response = client.get(f"/performance/lineage/{non_existent_id}")
    assert response.status_code == 404
