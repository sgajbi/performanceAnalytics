# engine/ror.py
import numpy as np
import pandas as pd
from engine.schema import PortfolioColumns
from engine.rules import calculate_resets


def calculate_daily_ror(df: pd.DataFrame, metric_basis: str) -> pd.Series:
    """Calculates the daily rate of return in a fully vectorized operation."""
    begin_mv = df[PortfolioColumns.BEGIN_MV].to_numpy()
    bod_cf = df[PortfolioColumns.BOD_CF].to_numpy()
    eod_cf = df[PortfolioColumns.EOD_CF].to_numpy()
    mgmt_fees = df[PortfolioColumns.MGMT_FEES].to_numpy()
    end_mv = df[PortfolioColumns.END_MV].to_numpy()
    
    numerator = end_mv - begin_mv - bod_cf - eod_cf
    if metric_basis == "NET":
        numerator += mgmt_fees

    denominator = np.abs(begin_mv + bod_cf)
    daily_ror = np.full(denominator.shape, 0.0, dtype=np.float64)
    
    is_after_start = (df[PortfolioColumns.PERF_DATE] >= df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]).to_numpy()
    safe_division_mask = (denominator != 0) & is_after_start
    
    np.divide(numerator, denominator, out=daily_ror, where=safe_division_mask)
    daily_ror[safe_division_mask] *= 100
    
    return pd.Series(daily_ror, index=df.index)


def calculate_cumulative_ror(df: pd.DataFrame, config):
    """Vectorized calculation of all cumulative return series."""
    # Step 1 & 2: Preliminary Compounding and Intermediate RORs
    df[PortfolioColumns.TEMP_LONG_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], 'long', use_resets=False)
    df[PortfolioColumns.TEMP_SHORT_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], 'short', use_resets=False)
    df[PortfolioColumns.LONG_CUM_ROR] = df[PortfolioColumns.TEMP_LONG_CUM_ROR]
    df[PortfolioColumns.SHORT_CUM_ROR] = df[PortfolioColumns.TEMP_SHORT_CUM_ROR]
    
    # Step 3: Calculate Resets
    report_end_ts = pd.to_datetime(config.report_end_date)
    df[PortfolioColumns.PERF_RESET] = calculate_resets(df, report_end_ts)
    
    # Step 4: Final Compounding with Resets
    df[PortfolioColumns.LONG_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], 'long', use_resets=True)
    df[PortfolioColumns.SHORT_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], 'short', use_resets=True)
    
    # FIX: Apply the reset to zero on the *same day* the reset occurs.
    is_reset_day = df[PortfolioColumns.PERF_RESET] == 1
    df.loc[is_reset_day, [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = 0.0

    # Step 5: Final carry-forward logic for NIP days
    is_nip = df[PortfolioColumns.NIP] == 1
    df.loc[is_nip, [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = np.nan
    df[[PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = df[[PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]].ffill().fillna(0)

    # Step 6: Final Linked Return
    df[PortfolioColumns.FINAL_CUM_ROR] = ((1 + df[PortfolioColumns.LONG_CUM_ROR] / 100) * (1 + df[PortfolioColumns.SHORT_CUM_ROR] / 100) - 1) * 100


def _compound_ror(df: pd.DataFrame, daily_ror: pd.Series, leg: str, use_resets=False) -> pd.Series:
    """Helper for vectorized geometric compounding with correct short-side math."""
    sign = df[PortfolioColumns.SIGN]
    
    if leg == 'long':
        is_leg_day = sign == 1
        growth_factor = 1 + (daily_ror / 100)
    else: # short
        is_leg_day = sign == -1
        growth_factor = 1 - (daily_ror / 100)

    growth_factor = growth_factor.where(is_leg_day, 1.0)
    
    is_period_start = df[PortfolioColumns.PERF_DATE] == df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]
    block_starts = is_period_start
    if use_resets:
        # FIX: A reset on day T starts a new block on that same day, so no shift is needed.
        block_starts |= (df[PortfolioColumns.PERF_RESET] == 1)

    block_ids = block_starts.cumsum()
    cumulative_growth = growth_factor.groupby(block_ids).cumprod()

    cumulative_ror = (cumulative_growth - 1) * 100
    if leg == 'short':
        cumulative_ror *= -1

    leg_ror = cumulative_ror.where(is_leg_day)
    return leg_ror.ffill().fillna(0)