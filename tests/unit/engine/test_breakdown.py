# tests/unit/engine/test_breakdown.py
from datetime import date
import pandas as pd
import pytest
from common.enums import Frequency
from engine.breakdown import generate_performance_breakdowns
from engine.schema import PortfolioColumns


@pytest.fixture
def sample_daily_results() -> pd.DataFrame:
    """Provides a sample daily performance DataFrame for testing breakdowns."""
    data = {
        PortfolioColumns.PERF_DATE: pd.to_datetime([
            "2025-01-30", "2025-01-31", "2025-02-01"
        ]).date,
        PortfolioColumns.BEGIN_MV: [100.0, 110.0, 121.0],
        PortfolioColumns.BOD_CF: [0.0, 0.0, 10.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [110.0, 121.0, 135.0],
        PortfolioColumns.DAILY_ROR: [10.0, 10.0, 3.030303],
    }
    return pd.DataFrame(data)


def test_generate_breakdowns_monthly(sample_daily_results):
    """Tests that monthly aggregation is calculated correctly."""
    # Act
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, frequencies=[Frequency.MONTHLY]
    )

    # Assert
    assert Frequency.MONTHLY in breakdowns
    assert len(breakdowns[Frequency.MONTHLY]) == 2 # Jan and Feb

    jan_results = breakdowns[Frequency.MONTHLY][0]
    assert jan_results["period"] == "2025-01"
    
    jan_summary = jan_results["summary"]
    assert jan_summary[PortfolioColumns.BEGIN_MV] == 100.0
    assert jan_summary[PortfolioColumns.END_MV] == 121.0
    assert jan_summary["net_cash_flow"] == 0.0
    assert jan_summary[PortfolioColumns.FINAL_CUM_ROR] == pytest.approx(21.0)
    
    feb_results = breakdowns[Frequency.MONTHLY][1]
    assert feb_results["period"] == "2025-02"
    feb_summary = feb_results["summary"]
    assert feb_summary[PortfolioColumns.BEGIN_MV] == 121.0
    assert feb_summary[PortfolioColumns.FINAL_CUM_ROR] == pytest.approx(3.030303)


def test_generate_breakdowns_yearly(sample_daily_results):
    """Tests that yearly aggregation is calculated correctly."""
    # Act
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, frequencies=[Frequency.YEARLY]
    )

    # Assert
    assert Frequency.YEARLY in breakdowns
    assert len(breakdowns[Frequency.YEARLY]) == 1 # Only one year

    y2025_results = breakdowns[Frequency.YEARLY][0]
    assert y2025_results["period"] == "2025"
    
    y2025_summary = y2025_results["summary"]
    assert y2025_summary[PortfolioColumns.BEGIN_MV] == 100.0
    assert y2025_summary[PortfolioColumns.END_MV] == 135.0
    assert y2025_summary["net_cash_flow"] == 10.0
    assert y2025_summary[PortfolioColumns.FINAL_CUM_ROR] == pytest.approx(24.666663)


def test_generate_breakdowns_multiple_frequencies(sample_daily_results):
    """Tests that the function returns multiple breakdowns when requested."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, frequencies=[Frequency.DAILY, Frequency.YEARLY]
    )
    assert Frequency.DAILY in breakdowns
    assert Frequency.YEARLY in breakdowns
    assert len(breakdowns[Frequency.DAILY]) == 3
    assert len(breakdowns[Frequency.YEARLY]) == 1


def test_generate_breakdowns_empty_input():
    """Tests that the function handles an empty DataFrame correctly."""
    breakdowns = generate_performance_breakdowns(
        pd.DataFrame(), frequencies=[Frequency.DAILY]
    )
    assert breakdowns == {}


def test_generate_breakdowns_quarterly(sample_daily_results):
    """Tests that quarterly aggregation is calculated correctly."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, frequencies=[Frequency.QUARTERLY]
    )
    assert Frequency.QUARTERLY in breakdowns
    assert len(breakdowns[Frequency.QUARTERLY]) == 1
    q1_results = breakdowns[Frequency.QUARTERLY][0]
    assert q1_results["period"] == "2025-Q1"