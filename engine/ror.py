# engine/ror.py
import warnings
from decimal import Decimal

import numpy as np
import pandas as pd
from engine.rules import calculate_initial_resets, calculate_nctrl4_reset
from engine.schema import PortfolioColumns


def calculate_daily_ror(df: pd.DataFrame, metric_basis: str) -> pd.Series:
    """Calculates the daily rate of return, supporting both float and Decimal."""
    is_decimal_mode = df[PortfolioColumns.BEGIN_MV].dtype == "object"

    if is_decimal_mode:
        numerator = (
            df[PortfolioColumns.END_MV] - df[PortfolioColumns.BOD_CF] -
            df[PortfolioColumns.BEGIN_MV] - df[PortfolioColumns.EOD_CF]
        )
        if metric_basis == "NET":
            numerator += df[PortfolioColumns.MGMT_FEES]

        denominator = (df[PortfolioColumns.BEGIN_MV] + df[PortfolioColumns.BOD_CF]).abs()
        daily_ror = pd.Series([Decimal(0)] * len(df), index=df.index)

        is_after_start = df[PortfolioColumns.PERF_DATE] >= df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]
        safe_division_mask = (denominator != Decimal(0)) & is_after_start

        if safe_division_mask.any():
            daily_ror.loc[safe_division_mask] = (
                numerator[safe_division_mask] / denominator[safe_division_mask]
            ) * Decimal(100)
        return daily_ror
    else:
        
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
    """Orchestrates all cumulative return calculations, supporting both float and Decimal."""
    is_decimal_mode = df[PortfolioColumns.DAILY_ROR].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0
    hundred = Decimal(100) if is_decimal_mode else 100.0
    one = Decimal(1) if is_decimal_mode else 1.0

    df[PortfolioColumns.TEMP_LONG_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], "long", use_resets=False)
    df[PortfolioColumns.TEMP_SHORT_CUM_ROR] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], "short", use_resets=False)

    report_end_ts = pd.to_datetime(config.report_end_date)
    initial_resets = calculate_initial_resets(df, report_end_ts)
    df[PortfolioColumns.PERF_RESET] = initial_resets.astype(int)

    final_long_ror = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], "long", use_resets=True)
    final_short_ror = _compound_ror(df, df[PortfolioColumns.DAILY_ROR], "short", use_resets=True)

    df[PortfolioColumns.LONG_CUM_ROR] = final_long_ror
    df[PortfolioColumns.SHORT_CUM_ROR] = final_short_ror
    is_initial_reset_day = df[PortfolioColumns.PERF_RESET] == 1
    df.loc[is_initial_reset_day, [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = zero

    nctrl4_resets = calculate_nctrl4_reset(df)
    df[PortfolioColumns.PERF_RESET] |= nctrl4_resets
    is_final_reset_day = df[PortfolioColumns.PERF_RESET] == 1
    df.loc[is_final_reset_day, [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = zero

    df[PortfolioColumns.TEMP_LONG_CUM_ROR] = final_long_ror
    df[PortfolioColumns.TEMP_SHORT_CUM_ROR] = final_short_ror

    is_nip = df[PortfolioColumns.NIP] == 1
    df.loc[is_nip, [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = np.nan
    df[[PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]] = df[
        [PortfolioColumns.LONG_CUM_ROR, PortfolioColumns.SHORT_CUM_ROR]
    ].ffill().fillna(zero)

    df[PortfolioColumns.FINAL_CUM_ROR] = (
        (one + df[PortfolioColumns.LONG_CUM_ROR] / hundred)
        * (one + df[PortfolioColumns.SHORT_CUM_ROR] / hundred)
        - one
    ) * hundred


def _compound_ror(df: pd.DataFrame, daily_ror: pd.Series, leg: str, use_resets=False) -> pd.Series:
    """Helper for geometric compounding, supporting both float and Decimal."""
    is_decimal_mode = daily_ror.dtype == "object"
    one = Decimal(1) if is_decimal_mode else 1.0
    hundred = Decimal(100) if is_decimal_mode else 100.0
    zero = Decimal(0) if is_decimal_mode else 0.0

    sign = df[PortfolioColumns.SIGN]
    if leg == "long":
        is_leg_day = sign == 1
        growth_factor = one + (daily_ror / hundred)
    else:
        is_leg_day = sign == -1
        growth_factor = one - (daily_ror / hundred)
    growth_factor = growth_factor.where(is_leg_day, one)

    is_period_start = df[PortfolioColumns.PERF_DATE] == df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE]
    block_starts = is_period_start
    if use_resets:
        prev_day_was_reset = df[PortfolioColumns.PERF_RESET].shift(1, fill_value=0) == 1
        block_starts |= prev_day_was_reset
    block_ids = block_starts.cumsum()

    if is_decimal_mode:
        # Slower path for Decimals, as cumprod is not supported
        def decimal_cumprod(series):
            result = series.copy()
            for i in range(1, len(series)):
                result.iloc[i] = result.iloc[i-1] * result.iloc[i]
            return result
        cumulative_growth = growth_factor.groupby(block_ids, group_keys=False).apply(decimal_cumprod)
    else:
        # Fast path for floats
        cumulative_growth = growth_factor.groupby(block_ids).cumprod()

    cumulative_ror = (cumulative_growth - one) * hundred
    if leg == "short":
        cumulative_ror *= -one
    leg_ror = cumulative_ror.where(is_leg_day)

    # FIX: Suppress known FutureWarning from pandas on object-dtype Series.
    # This warning is not an issue for our Decimal implementation.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        filled_ror = leg_ror.ffill().fillna(zero)

    return filled_ror