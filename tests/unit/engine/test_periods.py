# tests/unit/engine/test_periods.py
from datetime import date

import pandas as pd
import pytest
from common.enums import PeriodType
from engine.config import EngineConfig
from engine.periods import get_effective_period_start_dates
from engine.schema import PortfolioColumns


@pytest.fixture
def sample_dates() -> pd.Series:
    """Provides a sample Series of dates for testing."""
    return pd.to_datetime(
        pd.Series(
            [
                date(2023, 8, 15),
                date(2024, 2, 15),
                date(2024, 9, 1),
                date(2025, 4, 1),
            ],
            name=PortfolioColumns.PERF_DATE,
        )
    )


@pytest.mark.parametrize(
    "period_type, report_end_date, expected_dates",
    [
        (PeriodType.YTD, date(2025, 12, 31), ["2023-01-01", "2024-01-01", "2024-01-01", "2025-01-01"]),
        (PeriodType.MTD, date(2025, 12, 31), ["2023-08-01", "2024-02-01", "2024-09-01", "2025-04-01"]),
        (PeriodType.QTD, date(2025, 12, 31), ["2023-07-01", "2024-01-01", "2024-07-01", "2025-04-01"]),
        (PeriodType.ITD, date(2025, 12, 31), ["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"]),
        (PeriodType.Y1, date(2025, 8, 31), ["2024-09-01", "2024-09-01", "2024-09-01", "2024-09-01"]),
        (PeriodType.Y3, date(2025, 8, 31), ["2022-09-01", "2022-09-01", "2022-09-01", "2022-09-01"]),
        (PeriodType.Y5, date(2025, 8, 31), ["2020-09-01", "2020-09-01", "2020-09-01", "2020-09-01"]),
    ],
)
def test_get_effective_period_start_dates(sample_dates, period_type, report_end_date, expected_dates):
    """
    Tests that the effective period start dates are calculated correctly for all period types.
    """
    config = EngineConfig(
        performance_start_date=date(2020, 1, 1),
        report_end_date=report_end_date,
        metric_basis="NET",
        period_type=period_type,
    )

    result_series = get_effective_period_start_dates(sample_dates, config)
    expected_series = pd.to_datetime(pd.Series(expected_dates))

    pd.testing.assert_series_equal(
        result_series.reset_index(drop=True),
        expected_series.reset_index(drop=True),
        check_names=False,
    )