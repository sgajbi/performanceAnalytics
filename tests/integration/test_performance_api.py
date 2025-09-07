# tests/integration/test_performance_api.py
from uuid import uuid4
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from main import app
from engine.exceptions import EngineCalculationError, InvalidEngineInputError


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_calculate_twr_endpoint_happy_path_and_diagnostics(client):
    """Tests the /performance/twr endpoint and verifies the shared response footer."""
    payload = {
        "portfolio_number": "PORT_STANDARD_GROWTH",
        "performance_start_date": "2024-12-31",
        "metric_basis": "NET",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-05",
        "period_type": "YTD",
        "calculation_id": str(uuid4()),
        "rounding_precision": 6,
        "frequencies": ["daily", "monthly"],
        "daily_data": [
            {"day": 1, "perf_date": "2025-01-01", "begin_mv": 100000.0, "end_mv": 101000.0},
            {"day": 2, "perf_date": "2025-01-02", "begin_mv": 101000.0, "end_mv": 102010.0},
            {"day": 3, "perf_date": "2025-01-03", "begin_mv": 102010.0, "end_mv": 100989.9},
            {"day": 4, "perf_date": "2025-01-04", "begin_mv": 100989.9, "bod_cf": 25000.0, "end_mv": 127249.29},
            {"day": 5, "perf_date": "2025-01-05", "begin_mv": 127249.29, "end_mv": 125976.7971},
        ],
    }

    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200

    response_data = response.json()
    assert "calculation_id" in response_data
    assert "breakdowns" in response_data
    assert "meta" in response_data
    assert response_data["meta"]["engine_version"] is not None
    assert "diagnostics" in response_data
    assert response_data["diagnostics"]["nip_days"] == 0
    assert "audit" in response_data
    assert response_data["audit"]["counts"]["input_rows"] == 5


def test_calculate_twr_endpoint_decimal_strict_mode(client):
    """Tests that precision_mode=DECIMAL_STRICT is respected."""
    payload = {
        "portfolio_number": "PORT123",
        "performance_start_date": "2023-12-31",
        "metric_basis": "NET",
        "report_start_date": "2024-01-01",
        "report_end_date": "2024-01-05",
        "period_type": "YTD",
        "calculation_id": str(uuid4()),
        "frequencies": ["daily"],
        "precision_mode": "DECIMAL_STRICT",
        "daily_data": [
            {"day": 3, "perf_date": "2024-01-03", "begin_mv": 102500.0, "bod_cf": 5000.0, "mgmt_fees": -10.0, "end_mv": 108000.0}
        ],
    }

    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["meta"]["precision_mode"] == "DECIMAL_STRICT"
    daily_ror = response_data["breakdowns"]["daily"][0]["summary"]["period_return_pct"]
    assert Decimal(str(daily_ror)) == pytest.approx(Decimal("0.4558139535"))


def test_calculate_twr_endpoint_quarterly_weekly_annualized(client):
    """Tests quarterly and weekly breakdowns with annualization enabled."""
    payload = {
        "portfolio_number": "LONG_TEST",
        "performance_start_date": "2023-12-01",
        "metric_basis": "NET",
        "report_start_date": "2024-01-01",
        "report_end_date": "2024-05-31",
        "period_type": "YTD",
        "calculation_id": str(uuid4()),
        "frequencies": ["quarterly", "weekly"],
        "annualization": {"enabled": True, "basis": "BUS/252"},
        "daily_data": [
            {"day": 1, "perf_date": "2024-01-01", "begin_mv": 100000.0, "end_mv": 101000.0},
            {"day": 2, "perf_date": "2024-02-01", "begin_mv": 101000.0, "end_mv": 102000.0},
            {"day": 3, "perf_date": "2024-03-01", "begin_mv": 102000.0, "end_mv": 103000.0},
            {"day": 4, "perf_date": "2024-04-01", "begin_mv": 103000.0, "end_mv": 104000.0},
        ],
    }

    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    response_data = response.json()

    assert "quarterly" in response_data["breakdowns"]
    assert "weekly" in response_data["breakdowns"]
    q1 = response_data["breakdowns"]["quarterly"][0]
    assert q1["period"] == "2024-Q1"
    assert "annualized_return_pct" in q1["summary"]


def test_calculate_twr_with_empty_period(client):
    """Tests that the breakdown aggregator correctly handles periods with no data."""
    payload = {
        "portfolio_number": "EMPTY_PERIOD_TEST",
        "performance_start_date": "2024-12-31",
        "report_end_date": "2025-03-31",
        "metric_basis": "NET",
        "period_type": "YTD",
        "frequencies": ["monthly"],
        "daily_data": [
            {"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1010},
            {"day": 2, "perf_date": "2025-03-01", "begin_mv": 1010, "end_mv": 1020},
        ],
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()
    monthly_breakdown = data["breakdowns"]["monthly"]
    assert len(monthly_breakdown) == 2
    assert monthly_breakdown[0]["period"] == "2025-01"
    assert monthly_breakdown[1]["period"] == "2025-03"


@pytest.mark.parametrize(
    "error_class, expected_status",
    [(InvalidEngineInputError, 400), (EngineCalculationError, 500), (Exception, 500)],
)
def test_calculate_twr_endpoint_error_handling(client, mocker, error_class, expected_status):
    """Tests that the TWR endpoint correctly handles engine exceptions."""
    mocker.patch('app.api.endpoints.performance.run_calculations', side_effect=error_class("Test Error"))
    payload = {
        "portfolio_number": "ERROR_TEST", "performance_start_date": "2023-12-31", "metric_basis": "NET",
        "report_start_date": "2024-01-01", "report_end_date": "2024-01-05", "period_type": "YTD",
        "frequencies": ["daily"], "daily_data": [{"day": 1, "perf_date": "2024-01-01", "begin_mv": 1000.0, "end_mv": 1010.0}],
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == expected_status
    assert "detail" in response.json()