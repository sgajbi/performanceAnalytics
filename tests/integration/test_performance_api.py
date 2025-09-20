# tests/integration/test_performance_api.py
from uuid import uuid4
from decimal import Decimal
from datetime import date

import pytest
from fastapi.testclient import TestClient

from main import app
from engine.exceptions import EngineCalculationError, InvalidEngineInputError


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_calculate_twr_endpoint_legacy_path_and_diagnostics(client):
    """Tests the /performance/twr endpoint using the legacy 'period_type' and verifies the shared response footer."""
    payload = {
        "portfolio_number": "PORT_STANDARD_GROWTH",
        "performance_start_date": "2024-12-31",
        "metric_basis": "NET",
        "report_end_date": "2025-01-05",
        "period_type": "YTD",  # Using legacy field
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
    # Legacy structure is now nested inside results_by_period
    assert "results_by_period" in response_data
    assert "YTD" in response_data["results_by_period"]
    ytd_results = response_data["results_by_period"]["YTD"]
    assert "breakdowns" in ytd_results

    assert "meta" in response_data
    assert response_data["meta"]["engine_version"] is not None
    assert "diagnostics" in response_data
    assert response_data["diagnostics"]["nip_days"] == 0
    assert "audit" in response_data
    assert response_data["audit"]["counts"]["input_rows"] == 5


def test_calculate_twr_endpoint_multi_period(client):
    """Tests a multi-period request for MTD and YTD."""
    payload = {
        "portfolio_number": "MULTI_PERIOD_TEST",
        "performance_start_date": "2024-12-31",
        "metric_basis": "NET",
        "report_end_date": "2025-02-15",
        "as_of": "2025-02-15", # Explicit as_of for period resolution
        "periods": ["MTD", "YTD"], # New multi-period request
        "frequencies": ["monthly"],
        "daily_data": [
            {"day": 1, "perf_date": "2025-01-15", "begin_mv": 1000.0, "end_mv": 1010.0}, # +1.0%
            {"day": 2, "perf_date": "2025-02-10", "begin_mv": 1010.0, "end_mv": 1030.2}, # +2.0%
        ],
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "results_by_period" in data
    results = data["results_by_period"]
    assert "MTD" in results
    assert "YTD" in results

    # Validate MTD result (only Feb data)
    mtd_return = results["MTD"]["breakdowns"]["monthly"][0]["summary"]["period_return_pct"]
    assert mtd_return == pytest.approx(2.0)

    # Validate YTD result (Jan and Feb data compounded)
    ytd_return = results["YTD"]["breakdowns"]["monthly"][0]["summary"]["period_return_pct"]
    assert ytd_return == pytest.approx(3.02) # (1.01 * 1.02) - 1


def test_calculate_twr_endpoint_multi_currency(client):
    """Tests an end-to-end multi-currency TWR request."""
    payload = {
        "portfolio_number": "MULTI_CCY_API_TEST",
        "performance_start_date": "2024-12-31",
        "metric_basis": "GROSS",
        "report_end_date": "2025-01-02",
        "periods": ["ITD"],
        "frequencies": ["daily"],
        "daily_data": [
            {"day": 1, "perf_date": "2025-01-01", "begin_mv": 100.0, "end_mv": 102.0},
            {"day": 2, "perf_date": "2025-01-02", "begin_mv": 102.0, "end_mv": 103.02},
        ],
        "currency_mode": "BOTH",
        "report_ccy": "USD",
        "fx": {
            "rates": [
                {"date": "2024-12-31", "ccy": "EUR", "rate": 1.05},
                {"date": "2025-01-01", "ccy": "EUR", "rate": 1.08},
                {"date": "2025-01-02", "ccy": "EUR", "rate": 1.07},
            ]
        },
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()
    itd_result = data["results_by_period"]["ITD"]

    assert "portfolio_return" in itd_result
    assert itd_result["portfolio_return"]["local"] == pytest.approx(3.02)
    assert itd_result["portfolio_return"]["fx"] == pytest.approx(1.90476, abs=1e-5)
    # FIX: Correct the expected compounded base return value
    assert itd_result["portfolio_return"]["base"] == pytest.approx(4.98228, abs=1e-5)
    assert data["meta"]["report_ccy"] == "USD"


def test_calculate_twr_endpoint_with_data_policy(client):
    """Tests that a request with data_policy overrides and flagging works end-to-end."""
    payload = {
        "portfolio_number": "POLICY_TEST",
        "performance_start_date": "2024-12-27",
        "metric_basis": "NET",
        "report_end_date": "2025-01-03",
        "periods": ["ITD"],
        "frequencies": ["daily"],
        "daily_data": [
            # Add stable history for MAD calculation
            {"day": 1, "perf_date": "2024-12-28", "begin_mv": 1000.0, "end_mv": 1001.0},
            {"day": 2, "perf_date": "2024-12-29", "begin_mv": 1001.0, "end_mv": 1002.0},
            {"day": 3, "perf_date": "2024-12-30", "begin_mv": 1002.0, "end_mv": 1003.0},
            {"day": 4, "perf_date": "2024-12-31", "begin_mv": 1003.0, "end_mv": 1004.0},
            # Day to be overridden
            {"day": 5, "perf_date": "2025-01-01", "begin_mv": 1004.0, "end_mv": 1010.0},
            # Outlier Day, with corrected begin_mv
            {"day": 6, "perf_date": "2025-01-02", "begin_mv": 1005.0, "end_mv": 2000.0},
            # Day to be ignored, with corrected begin_mv
            {"day": 7, "perf_date": "2025-01-03", "begin_mv": 2000.0, "end_mv": 2020.0},
        ],
        "data_policy": {
            "overrides": {"market_values": [{"perf_date": "2025-01-01", "end_mv": 1005.0}]},
            "ignore_days": [{"entity_type": "PORTFOLIO", "entity_id": "POLICY_TEST", "dates": ["2025-01-03"]}],
            "outliers": {"enabled": True, "action": "FLAG", "params": {"mad_k": 3.0}},
        },
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()
    itd_result = data["results_by_period"]["ITD"]

    # Assert override was applied (index 4 in results)
    daily_breakdown = itd_result["breakdowns"]["daily"]
    assert daily_breakdown[4]["summary"]["period_return_pct"] == pytest.approx(0.099602, abs=1e-6)

    # Assert ignore_days was applied (index 6 in results)
    assert daily_breakdown[6]["summary"]["period_return_pct"] == 0.0

    # Assert diagnostics are correct
    diags = data["diagnostics"]
    assert diags["policy"]["overrides"]["applied_mv_count"] == 1
    assert diags["policy"]["ignored_days_count"] == 1
    assert diags["policy"]["outliers"]["flagged_rows"] == 1


@pytest.mark.parametrize(
    "error_class, expected_status",
    [(InvalidEngineInputError, 400), (EngineCalculationError, 500), (Exception, 500)],
)
def test_calculate_twr_endpoint_error_handling(client, mocker, error_class, expected_status):
    """Tests that the TWR endpoint correctly handles engine exceptions."""
    mocker.patch("app.api.endpoints.performance.run_calculations", side_effect=error_class("Test Error"))
    payload = {
        "portfolio_number": "ERROR_TEST",
        "performance_start_date": "2023-12-31",
        "metric_basis": "NET",
        "report_end_date": "2024-01-05",
        "periods": ["YTD"],
        "frequencies": ["daily"],
        "daily_data": [{"day": 1, "perf_date": "2024-01-01", "begin_mv": 1000.0, "end_mv": 1010.0}],
    }
    response = client.post("/performance/twr", json=payload)
    assert response.status_code == expected_status
    assert "detail" in response.json()