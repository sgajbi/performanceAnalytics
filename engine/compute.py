# engine/compute.py
import logging

import pandas as pd
from app.core.exceptions import CalculationLogicError, InvalidInputDataError
from engine.config import EngineConfig
from engine.ror import calculate_daily_ror, calculate_cumulative_ror
from engine.schema import PortfolioColumns
from engine.periods import get_effective_period_start_dates
from engine.rules import calculate_sign, calculate_nip

logger = logging.getLogger(__name__)


def run_calculations(df: pd.DataFrame, config: EngineConfig) -> pd.DataFrame:
    """
    Orchestrates the full portfolio performance calculation pipeline using
    a fully vectorized approach.
    """
    if df.empty:
        return pd.DataFrame()

    try:
        # Step 1: Preparation & Initialization
        _prepare_dataframe(df)

        # Step 2: Foundational Vectorized Calculations
        df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE] = get_effective_period_start_dates(
            df[PortfolioColumns.PERF_DATE], config
        )
        df[PortfolioColumns.DAILY_ROR] = calculate_daily_ror(
            df, config.metric_basis
        )
        
        df[PortfolioColumns.PERF_RESET] = 0 # Must be initialized before sign calculation
        df[PortfolioColumns.SIGN] = calculate_sign(df)
        df[PortfolioColumns.NIP] = calculate_nip(df)

        # Step 3: Complex Cumulative & Rule-Based Calculations
        calculate_cumulative_ror(df, config)

        # Step 4: Final Formatting & Precision Handling
        df[PortfolioColumns.LONG_SHORT] = df[PortfolioColumns.SIGN].apply(
            lambda x: "S" if x == -1 else "L"
        )
        final_df = _filter_results_to_reporting_period(df, config)
        
        # FIX: Round float columns to handle precision differences between float64 and legacy Decimal
        _round_float_columns(final_df)

    except Exception as e:
        logger.exception("An unexpected error occurred during engine calculations.")
        raise CalculationLogicError(f"Engine calculation failed: {e}")

    logger.info("Performance engine calculation complete.")
    return final_df


def _prepare_dataframe(df: pd.DataFrame):
    """Initializes and prepares the DataFrame for vectorized calculation."""
    numeric_cols = [
        PortfolioColumns.DAY, PortfolioColumns.BEGIN_MV, PortfolioColumns.BOD_CF,
        PortfolioColumns.EOD_CF, PortfolioColumns.MGMT_FEES, PortfolioColumns.END_MV,
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df[PortfolioColumns.PERF_DATE] = pd.to_datetime(df[PortfolioColumns.PERF_DATE], errors="coerce")
    if df[PortfolioColumns.PERF_DATE].isnull().any():
        raise InvalidInputDataError("One or more 'perf_date' values are invalid or missing.")

    for col in PortfolioColumns:
        if col not in df.columns and col not in [PortfolioColumns.LONG_SHORT, PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]:
            df[col] = 0.0
    df[PortfolioColumns.LONG_SHORT] = ""


def _filter_results_to_reporting_period(df: pd.DataFrame, config: EngineConfig) -> pd.DataFrame:
    """Filters the DataFrame to only include dates within the reporting period."""
    effective_report_start = pd.to_datetime(config.performance_start_date)
    if config.report_start_date:
        effective_report_start = max(effective_report_start, pd.to_datetime(config.report_start_date))
    report_end_date = pd.to_datetime(config.report_end_date)

    mask = (df[PortfolioColumns.PERF_DATE] >= effective_report_start) & (df[PortfolioColumns.PERF_DATE] <= report_end_date)
    
    final_df = df[mask].copy()
    final_df.drop(columns=[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE], inplace=True, errors='ignore')
    
    final_df[PortfolioColumns.PERF_DATE] = final_df[PortfolioColumns.PERF_DATE].dt.date
    
    return final_df

def _round_float_columns(df: pd.DataFrame):
    """Rounds float columns to a standard precision to ensure consistency."""
    float_cols = df.select_dtypes(include=['float64']).columns
    df[float_cols] = df[float_cols].round(10) # Round to 10 decimal places