# tests/unit/engine/test_compute.py
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from engine.config import EngineConfig, PeriodType, PrecisionMode
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
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

    result_df, _ = run_calculations(df.copy(), config)

    assert isinstance(result_df[PortfolioColumns.DAILY_ROR].iloc[0], Decimal)
    expected_ror = Decimal("0.754")
    assert result_df[PortfolioColumns.DAILY_ROR].iloc[0] == pytest.approx(expected_ror)


def test_run_calculations_empty_dataframe():
    """Tests that the engine handles an empty DataFrame without errors."""
    config = EngineConfig(
        performance_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 1),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    empty_df = pd.DataFrame()
    result, _ = run_calculations(empty_df, config)
    assert result.empty


def test_run_calculations_float_mode_rounding():
    """Tests that rounding is applied correctly in the default FLOAT64 mode."""
    config = EngineConfig(
        performance_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 1),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    data = {
        PortfolioColumns.PERF_DATE: [date(2025, 1, 1)],
        PortfolioColumns.BEGIN_MV: [100.0],
        PortfolioColumns.BOD_CF: [0.0],
        PortfolioColumns.EOD_CF: [0.0],
        PortfolioColumns.MGMT_FEES: [0.0],
        PortfolioColumns.END_MV: [101.12345678912345],
    }
    df = pd.DataFrame(data)
    result_df, _ = run_calculations(df, config)
    # FIX: The EngineConfig default rounding_precision is 4.
    assert result_df[PortfolioColumns.DAILY_ROR].iloc[0] == 1.1235


def test_run_calculations_general_exception_handling():
    """Tests that an invalid input type raises an InvalidEngineInputError."""
    config = EngineConfig(
        performance_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 1),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    bad_df = {"not_a": "dataframe"}

    with pytest.raises(InvalidEngineInputError) as exc_info:
        run_calculations(bad_df, config)

    assert "Input must be a pandas DataFrame" in exc_info.value.message