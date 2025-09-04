# tests/unit/engine/test_ror.py
from datetime import date
import pandas as pd
import pytest
from engine.ror import calculate_daily_ror
from engine.schema import PortfolioColumns
from engine.periods import get_effective_period_start_dates
from engine.config import EngineConfig

@pytest.fixture
def sample_df():
    """Provides a sample DataFrame for RoR tests."""
    data = [
        {PortfolioColumns.PERF_DATE: date(2025, 1, 1), PortfolioColumns.BEGIN_MV: 1000, PortfolioColumns.BOD_CF: 0, PortfolioColumns.EOD_CF: 0, PortfolioColumns.MGMT_FEES: -10, PortfolioColumns.END_MV: 1090},
        {PortfolioColumns.PERF_DATE: date(2025, 1, 2), PortfolioColumns.BEGIN_MV: 1090, PortfolioColumns.BOD_CF: 0, PortfolioColumns.EOD_CF: 0, PortfolioColumns.MGMT_FEES: -10, PortfolioColumns.END_MV: 1200},
        {PortfolioColumns.PERF_DATE: date(2025, 1, 3), PortfolioColumns.BEGIN_MV: 0, PortfolioColumns.BOD_CF: 0, PortfolioColumns.EOD_CF: 0, PortfolioColumns.MGMT_FEES: 0, PortfolioColumns.END_MV: 10},
        {PortfolioColumns.PERF_DATE: date(2025, 1, 4), PortfolioColumns.BEGIN_MV: 100, PortfolioColumns.BOD_CF: 0, PortfolioColumns.EOD_CF: 0, PortfolioColumns.MGMT_FEES: 0, PortfolioColumns.END_MV: 110},
    ]
    df = pd.DataFrame(data)
    
    # FIX: Convert the date column to datetime64 immediately, as the engine does.
    # This ensures the test fixture provides the correct dtype to the functions it tests.
    df[PortfolioColumns.PERF_DATE] = pd.to_datetime(df[PortfolioColumns.PERF_DATE])
    
    config = EngineConfig(
        performance_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 31),
        metric_basis="NET",
        period_type="YTD",
        report_start_date=date(2025, 1, 4)
    )
    
    df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE] = get_effective_period_start_dates(df[PortfolioColumns.PERF_DATE], config)
    return df

def test_daily_ror_net_basis(sample_df):
    """Tests that NET RoR correctly includes management fees."""
    # (1090 - 1000 - 0 - 0 + (-10)) / (1000 + 0) = 80 / 1000 = 0.08 -> 8%
    ror_series = calculate_daily_ror(sample_df, metric_basis="NET")
    assert ror_series.iloc[0] == pytest.approx(8.0)

def test_daily_ror_gross_basis(sample_df):
    """Tests that GROSS RoR correctly ignores management fees."""
    # (1200 - 1090 - 0 - 0) / (1090 + 0) = 110 / 1090 * 100 ~= 10.0917%
    ror_series = calculate_daily_ror(sample_df, metric_basis="GROSS")
    assert ror_series.iloc[1] == pytest.approx(10.091743119)

def test_daily_ror_zero_denominator(sample_df):
    """Tests that RoR is 0 when the denominator is 0."""
    ror_series = calculate_daily_ror(sample_df, metric_basis="NET")
    assert ror_series.iloc[2] == 0.0

def test_daily_ror_before_effective_start(sample_df):
    """Tests that RoR is 0 for dates before the effective period start."""
    config = EngineConfig(
        performance_start_date=date(2025, 1, 5),
        report_end_date=date(2025, 1, 31),
        metric_basis="NET", period_type="YTD"
    )
    df = sample_df.copy()
    df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE] = get_effective_period_start_dates(df[PortfolioColumns.PERF_DATE], config)
    
    ror_series = calculate_daily_ror(df, metric_basis="NET")
    assert ror_series.iloc[3] == 0.0