# tests/unit/engine/test_periods.py
from datetime import date

import pandas as pd
import pytest
from engine.config import EngineConfig, PeriodType
from engine.periods import get_effective_period_start_dates
from engine.schema import PortfolioColumns


@pytest.fixture
def sample_dates() -> pd.Series:
    """Provides a sample Series of dates for testing."""
    return pd.to_datetime(
        pd.Series(
            [
                date(2025, 1, 1),
                date(2025, 2, 15),
                date(2025, 3, 31),
                date(2025, 4, 1),
            ],
            name=PortfolioColumns.PERF_DATE,
        )
    )


@pytest.mark.parametrize(
    "period_type, performance_start_date, expected_dates",
    [
        (
            PeriodType.YTD,
            date(2025, 1, 1),
            [
                "2025-01-01",
                "2025-01-01",
                "2025-01-01",
                "2025-01-01",
            ],
        ),
        (
            PeriodType.MTD,
            date(2025, 1, 1),
            [
                "2025-01-01",
                "2025-02-01",
                "2025-03-01",
                "2025-04-01",
            ],
        ),
        (
            PeriodType.QTD,
            date(2025, 1, 1),
            [
                "2025-01-01",
                "2025-01-01",
                "2025-01-01",
                "2025-04-01",
            ],
        ),
        (
            PeriodType.EXPLICIT,
            date(2025, 2, 1),
            [
                "2025-02-01",
                "2025-02-01",
                "2025-02-01",
                "2025-02-01",
            ],
        ),
    ],
)
def test_get_effective_period_start_dates(
    sample_dates, period_type, performance_start_date, expected_dates
):
    """
    Tests that the effective period start dates are calculated correctly
    for all period types (YTD, MTD, QTD, Explicit).
    """
    config = EngineConfig(
        performance_start_date=performance_start_date,
        report_end_date=date(2025, 12, 31),
        metric_basis="NET",
        period_type=period_type,
        report_start_date=performance_start_date,  # Align for simplicity
    )

    result_series = get_effective_period_start_dates(sample_dates, config)
    expected_series = pd.to_datetime(pd.Series(expected_dates))

    pd.testing.assert_series_equal(
        result_series.reset_index(drop=True),
        expected_series.reset_index(drop=True),
        check_names=False,  # Ignore the 'name' attribute for the comparison
    )