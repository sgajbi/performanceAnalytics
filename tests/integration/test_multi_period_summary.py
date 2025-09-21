# tests/integration/test_multi_period_summary.py
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_multi_period_portfolio_return_summary_is_correct(client):
    """
    Tests that in a multi-period request, the portfolio_return summary object
    for each period correctly reflects that period's return, not the master
    period's return. This test specifically validates the fix for this bug.
    """
    payload = {
        "portfolio_number": "MULTI_PERIOD_SUMMARY_TEST",
        "performance_start_date": "2024-12-31",
        "as_of": "2025-02-28",
        "report_end_date": "2025-02-28",
        "periods": ["MTD", "YTD"],
        "metric_basis": "GROSS",
        "frequencies": ["monthly"],
        "currency_mode": "BOTH",
        "report_ccy": "USD",
        "daily_data": [
            # Jan Data: Local +1%, FX +1% -> Base +2.01%
            {"day": 1, "perf_date": "2025-01-15", "begin_mv": 100.0, "end_mv": 101.0},
            # Feb Data: Local +2%, FX +2% -> Base +4.04%
            {"day": 2, "perf_date": "2025-02-15", "begin_mv": 101.0, "end_mv": 103.02},
        ],
        "fx": {
            "rates": [
                {"date": "2024-12-31", "ccy": "EUR", "rate": 1.00},
                {"date": "2025-01-15", "ccy": "EUR", "rate": 1.01},
                {"date": "2025-02-15", "ccy": "EUR", "rate": 1.0302},
            ]
        },
    }

    response = client.post("/performance/twr", json=payload)
    assert response.status_code == 200
    data = response.json()

    results = data["results_by_period"]
    assert "MTD" in results
    assert "YTD" in results

    mtd_summary = results["MTD"]["portfolio_return"]
    ytd_summary = results["YTD"]["portfolio_return"]

    # Assert MTD summary is correct for February (~4.04%)
    assert mtd_summary["local"] == pytest.approx(2.0)
    assert mtd_summary["fx"] == pytest.approx(2.0)
    assert mtd_summary["base"] == pytest.approx(4.04)

    # Assert YTD summary is correct for Jan + Feb
    # Compounded Local: (1.01 * 1.02) - 1 = 3.02%
    # Compounded FX: (1.01 * 1.02) - 1 = 3.02%
    # Compounded Base: (1.0201 * 1.0404) - 1 = 6.13248...%
    assert ytd_summary["local"] == pytest.approx(3.02)
    assert ytd_summary["fx"] == pytest.approx(3.02)
    assert ytd_summary["base"] == pytest.approx(6.132484)

    # Crucially, assert the MTD and YTD summaries are NOT the same
    assert mtd_summary["base"] != ytd_summary["base"]