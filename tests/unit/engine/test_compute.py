# tests/unit/engine/test_compute.py
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from engine.config import EngineConfig, PeriodType, PrecisionMode
from engine.compute import run_calculations
from engine.schema import PortfolioColumns


def test_run_calculations_decimal_strict_mode():
    """
    Tests that when PrecisionMode.DECIMAL_STRICT is used, the calculations
    are performed using Decimal objects, not floats.
    """
    config = EngineConfig(
        performance_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 1),
        metric_basis="NET",
        period_type=PeriodType.YTD,
        precision_mode=PrecisionMode.DECIMAL_STRICT,
    )

    # Input data uses Decimal objects
    data = {
        PortfolioColumns.DAY: [1],
        PortfolioColumns.PERF_DATE: [pd.to_datetime("2025-01-01")],
        PortfolioColumns.BEGIN_MV: [Decimal("1000.0")],
        PortfolioColumns.BOD_CF: [Decimal("0.0")],
        PortfolioColumns.EOD_CF: [Decimal("0.0")],
        PortfolioColumns.MGMT_FEES: [Decimal("-1.23")],
        PortfolioColumns.END_MV: [Decimal("1008.77")],
    }
    df = pd.DataFrame(data)

    # This call is expected to fail until we implement the DECIMAL_STRICT path
    result_df = run_calculations(df.copy(), config)

    # Assert that the output contains Decimal types, not float
    assert isinstance(result_df[PortfolioColumns.DAILY_ROR].iloc[0], Decimal)

    # (1008.77 - 1000.0 - 0 - 0 + (-1.23)) / 1000.0 = 7.54 / 1000 = 0.00754 -> 0.754%
    expected_ror = Decimal("0.754")
    assert result_df[PortfolioColumns.DAILY_ROR].iloc[0] == expected_ror