# engine/compute.py
import logging
from decimal import Decimal

import numpy as np
import pandas as pd
from engine.config import EngineConfig, PrecisionMode
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
from engine.periods import get_effective_period_start_dates
from engine.ror import calculate_cumulative_ror, calculate_daily_ror
from engine.rules import calculate_nip, calculate_sign
from engine.schema import PortfolioColumns

logger = logging.getLogger(__name__)


def run_calculations(df: pd.DataFrame, config: EngineConfig) -> pd.DataFrame:
    """
    Orchestrates the full portfolio performance calculation pipeline using
    a fully vectorized approach.
    """
    if df.empty:
        return pd.DataFrame()

    try:
        # Step 1: Preparation & Initialization (now precision-aware)
        _prepare_dataframe(df, config)

        # Step 2: Foundational Vectorized Calculations
        df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE] = get_effective_period_start_dates(
            df[PortfolioColumns.PERF_DATE], config
        )
        df[PortfolioColumns.DAILY_ROR] = calculate_daily_ror(df, config.metric_basis)

        df[PortfolioColumns.PERF_RESET] = 0  # Must be initialized before sign calculation
        df[PortfolioColumns.SIGN] = calculate_sign(df)
        df[PortfolioColumns.NIP] = calculate_nip(df, config) # Pass config for feature flag access

        # Step 3: Complex Cumulative & Rule-Based Calculations
        calculate_cumulative_ror(df, config)

        # Step 4: Final Formatting & Precision Handling
        df[PortfolioColumns.LONG_SHORT] = np.where(df[PortfolioColumns.SIGN] == -1, "S", "L")

        final_df = _filter_results_to_reporting_period(df, config)

        # Round float columns only if not in strict decimal mode
        if config.precision_mode != PrecisionMode.DECIMAL_STRICT:
            _round_float_columns(final_df)

    except Exception as e:
        logger.exception("An unexpected error occurred during engine calculations.")
        # Wrap unexpected errors in our engine-specific exception
        raise EngineCalculationError(f"Engine calculation failed unexpectedly: {e}")

    logger.info("Performance engine calculation complete.")
    return final_df


def _prepare_dataframe(df: pd.DataFrame, config: EngineConfig):
    """Initializes and prepares the DataFrame for calculation, handling precision mode."""
    numeric_cols = [
        PortfolioColumns.DAY,
        PortfolioColumns.BEGIN_MV,
        PortfolioColumns.BOD_CF,
        PortfolioColumns.EOD_CF,
        PortfolioColumns.MGMT_FEES,
        PortfolioColumns.END_MV,
    ]

    # Convert numeric columns based on the selected precision mode
    if config.precision_mode == PrecisionMode.DECIMAL_STRICT:
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal(0))
    else:  # Default to float64
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df[PortfolioColumns.PERF_DATE] = pd.to_datetime(df[PortfolioColumns.PERF_DATE], errors="coerce")
    if df[PortfolioColumns.PERF_DATE].isnull().any():
        raise InvalidEngineInputError("One or more 'perf_date' values are invalid or missing.")

    for col in PortfolioColumns:
        if col not in df.columns and col not in [PortfolioColumns.LONG_SHORT, PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]:
            # Initialize with the correct type based on precision mode
            df[col] = Decimal(0) if config.precision_mode == PrecisionMode.DECIMAL_STRICT else 0.0
    df[PortfolioColumns.LONG_SHORT] = ""


def _filter_results_to_reporting_period(df: pd.DataFrame, config: EngineConfig) -> pd.DataFrame:
    """Filters the DataFrame to only include dates within the reporting period."""
    effective_report_start = pd.to_datetime(config.performance_start_date)
    if config.report_start_date:
        effective_report_start = max(effective_report_start, pd.to_datetime(config.report_start_date))
    report_end_date = pd.to_datetime(config.report_end_date)

    mask = (df[PortfolioColumns.PERF_DATE] >= effective_report_start) & (df[PortfolioColumns.PERF_DATE] <= report_end_date)

    final_df = df[mask].copy()
    final_df.drop(columns=[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE], inplace=True, errors="ignore")

    final_df[PortfolioColumns.PERF_DATE] = final_df[PortfolioColumns.PERF_DATE].dt.date

    return final_df


def _round_float_columns(df: pd.DataFrame):
    """Rounds float columns to a standard precision to ensure consistency."""
    float_cols = df.select_dtypes(include=["float64"]).columns
    df[float_cols] = df[float_cols].round(10)  # Round to 10 decimal places