# tests/unit/engine/test_breakdown.py
from datetime import date
import pandas as pd
import pytest
from common.enums import Frequency
from core.envelope import Annualization
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
        PortfolioColumns.FINAL_CUM_ROR: [21.0, 21.0, 24.666663], # Dummy cumulative
    }
    return pd.DataFrame(data)


@pytest.fixture
def default_annualization() -> Annualization:
    """Provides a default, disabled Annualization config."""
    return Annualization(enabled=False)


def test_generate_breakdowns_monthly(sample_daily_results, default_annualization):
    """Tests that monthly aggregation is calculated correctly."""
    # FIX: Pass new required arguments
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.MONTHLY], default_annualization, False
    )

    assert Frequency.MONTHLY in breakdowns
    assert len(breakdowns[Frequency.MONTHLY]) == 2
    jan_results = breakdowns[Frequency.MONTHLY][0]
    assert jan_results["period"] == "2025-01"
    jan_summary = jan_results["summary"]
    assert jan_summary["period_return_pct"] == pytest.approx(21.0)
    

def test_generate_breakdowns_yearly(sample_daily_results, default_annualization):
    """Tests that yearly aggregation is calculated correctly."""
    # FIX: Pass new required arguments
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.YEARLY], default_annualization, False
    )

    assert Frequency.YEARLY in breakdowns
    assert len(breakdowns[Frequency.YEARLY]) == 1
    y2025_results = breakdowns[Frequency.YEARLY][0]
    assert y2025_results["period"] == "2025"
    y2025_summary = y2025_results["summary"]
    assert y2025_summary["period_return_pct"] == pytest.approx(24.666663)


def test_generate_breakdowns_multiple_frequencies(sample_daily_results, default_annualization):
    """Tests that the function returns multiple breakdowns when requested."""
    # FIX: Pass new required arguments
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.DAILY, Frequency.YEARLY], default_annualization, False
    )
    assert Frequency.DAILY in breakdowns
    assert Frequency.YEARLY in breakdowns


def test_generate_breakdowns_empty_input(default_annualization):
    """Tests that the function handles an empty DataFrame correctly."""
    # FIX: Pass new required arguments
    breakdowns = generate_performance_breakdowns(
        pd.DataFrame(), [Frequency.DAILY], default_annualization, False
    )
    assert breakdowns == {}


def test_generate_breakdowns_quarterly(sample_daily_results, default_annualization):
    """Tests that quarterly aggregation is calculated correctly."""
    # FIX: Pass new required arguments
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.QUARTERLY], default_annualization, False
    )
    assert Frequency.QUARTERLY in breakdowns
    assert len(breakdowns[Frequency.QUARTERLY]) == 1
    q1_results = breakdowns[Frequency.QUARTERLY][0]
    assert q1_results["period"] == "2025-Q1"