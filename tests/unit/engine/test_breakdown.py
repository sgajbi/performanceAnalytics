# tests/unit/engine/test_breakdown.py
from datetime import date
import pandas as pd
import pytest
from common.enums import Frequency
from core.envelope import Annualization
from engine.breakdown import generate_performance_breakdowns, _calculate_period_summary_dict
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
        PortfolioColumns.FINAL_CUM_ROR: [10.0, 21.0, 24.666663],
    }
    return pd.DataFrame(data)


@pytest.fixture
def default_annualization() -> Annualization:
    """Provides a default, disabled Annualization config."""
    return Annualization(enabled=False)


def test_generate_breakdowns_monthly(sample_daily_results, default_annualization):
    """Tests that monthly aggregation is calculated correctly."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.MONTHLY], default_annualization, True, rounding_precision=6
    )

    assert Frequency.MONTHLY in breakdowns
    assert len(breakdowns[Frequency.MONTHLY]) == 2
    
    jan_results = breakdowns[Frequency.MONTHLY][0]
    assert jan_results["period"] == "2025-01"
    jan_summary = jan_results["summary"]
    assert jan_summary["period_return_pct"] == pytest.approx(21.0)
    assert jan_summary["cumulative_return_pct_to_date"] == pytest.approx(21.0)

    feb_results = breakdowns[Frequency.MONTHLY][1]
    assert feb_results["period"] == "2025-02"
    feb_summary = feb_results["summary"]
    assert feb_summary["period_return_pct"] == pytest.approx(3.030303)
    assert feb_summary["cumulative_return_pct_to_date"] == pytest.approx(24.666663)
    

def test_generate_breakdowns_yearly(sample_daily_results, default_annualization):
    """Tests that yearly aggregation is calculated correctly."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.YEARLY], default_annualization, False, rounding_precision=6
    )

    assert Frequency.YEARLY in breakdowns
    assert len(breakdowns[Frequency.YEARLY]) == 1
    y2025_results = breakdowns[Frequency.YEARLY][0]
    assert y2025_results["period"] == "2025"
    y2025_summary = y2025_results["summary"]
    assert y2025_summary["period_return_pct"] == pytest.approx(24.666663)


def test_generate_breakdowns_multiple_frequencies(sample_daily_results, default_annualization):
    """Tests that the function returns multiple breakdowns when requested."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.DAILY, Frequency.YEARLY], default_annualization, False, rounding_precision=6
    )
    assert Frequency.DAILY in breakdowns
    assert Frequency.YEARLY in breakdowns


def test_generate_breakdowns_empty_input(default_annualization):
    """Tests that the function handles an empty DataFrame correctly."""
    breakdowns = generate_performance_breakdowns(
        pd.DataFrame(), [Frequency.DAILY], default_annualization, False, rounding_precision=6
    )
    assert breakdowns == {}


def test_generate_breakdowns_quarterly(sample_daily_results, default_annualization):
    """Tests that quarterly aggregation is calculated correctly."""
    breakdowns = generate_performance_breakdowns(
        sample_daily_results, [Frequency.QUARTERLY], default_annualization, False, rounding_precision=6
    )
    assert Frequency.QUARTERLY in breakdowns
    # --- START FIX: Correct typo ---
    assert len(breakdowns[Frequency.QUARTERLY]) == 1
    # --- END FIX ---
    q1_results = breakdowns[Frequency.QUARTERLY][0]
    assert q1_results["period"] == "2025-Q1"


def test_annualization_correctly_handles_sparse_long_period():
    """
    Tests the annualization logic.
    A sparse (e.g., monthly) series over a
    year-long period should be annualized.
    """
    year_long_sparse_data = {
        PortfolioColumns.PERF_DATE: [date(2024, 1, 1), date(2024, 12, 31)],
        PortfolioColumns.DAILY_ROR: [2.0, 2.94117647],
        PortfolioColumns.BEGIN_MV: [100.0, 102.0],
        PortfolioColumns.END_MV: [102.0, 105.0],
        PortfolioColumns.BOD_CF: [0.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0],
        PortfolioColumns.FINAL_CUM_ROR: [2.0, 5.0],
    }
    df = pd.DataFrame(year_long_sparse_data)
    df_indexed = df.set_index(pd.to_datetime(df[PortfolioColumns.PERF_DATE]))
    
    annualization_config = Annualization(enabled=True, basis="ACT/365")

    summary = _calculate_period_summary_dict(df_indexed, df_indexed, annualization_config, False, rounding_precision=6)

    assert "annualized_return_pct" in summary
    assert summary["annualized_return_pct"] == pytest.approx(4.986004, abs=1e-6)
