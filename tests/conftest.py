# tests/conftest.py
import pytest


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