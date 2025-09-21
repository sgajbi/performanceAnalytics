# tests/conftest.py
import pytest


@pytest.fixture(scope="module")
def happy_path_payload():
    """Provides a standard, valid snake_case payload for contribution tests."""
    return {
        "portfolio_number": "CONTRIB_TEST_01",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-02",
        "period_type": "ITD",
        "portfolio_data": {
            "metric_basis": "NET",
            "valuation_points": [
                {"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1020, "bod_cf": 0, "eod_cf": 0, "mgmt_fees": 0},
                {"day": 2, "perf_date": "2025-01-02", "begin_mv": 1020, "end_mv": 1080, "bod_cf": 50, "eod_cf": 0, "mgmt_fees": 0},
            ],
        },
        "positions_data": [
            {
                "position_id": "Stock_A",
                "meta": {"sector": "Technology"},
                "valuation_points": [
                    {"day": 1, "perf_date": "2025-01-01", "begin_mv": 600, "end_mv": 612, "bod_cf": 0, "eod_cf": 0, "mgmt_fees": 0},
                    {"day": 2, "perf_date": "2025-01-02", "begin_mv": 612, "end_mv": 670, "bod_cf": 50, "eod_cf": 0, "mgmt_fees": 0},
                ],
            }
        ],
    }