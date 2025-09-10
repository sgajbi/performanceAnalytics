# engine/ror.py
import warnings
from decimal import Decimal

import numpy as np
import pandas as pd
from engine.config import EngineConfig
from engine.rules import calculate_initial_resets, calculate_nctrl4_reset
from engine.schema import PortfolioColumns


def calculate_daily_ror(df: pd.DataFrame, metric_basis: str, config: EngineConfig = None) -> pd.DataFrame:
    """
    Calculates the daily rate of return, supporting both float and Decimal.
    If FX config is provided, it returns a DataFrame with local, fx, and base returns.
    Otherwise, it returns a DataFrame with a single daily_ror column.
    """
    is_decimal_mode = df[PortfolioColumns.BEGIN_MV.value].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0
    hundred = Decimal(100) if is_decimal_mode else 100.0

    # --- 1. Calculate Local Rate of Return ---
    if is_decimal_mode:
        numerator = (
            df[PortfolioColumns.END_MV.value] - df[PortfolioColumns.BOD_CF.value] -
            df[PortfolioColumns.BEGIN_MV.value] - df[PortfolioColumns.EOD_CF.value]
        )
        if metric_basis == "NET":
            numerator += df[PortfolioColumns.MGMT_FEES.value]

        denominator = (df[PortfolioColumns.BEGIN_MV.value] + df[PortfolioColumns.BOD_CF.value]).abs()
        local_ror = pd.Series([zero] * len(df), index=df.index, dtype=object)
    else:
        numerator = (df[PortfolioColumns.END_MV.value] - df[PortfolioColumns.BOD_CF.value] -
                     df[PortfolioColumns.BEGIN_MV.value] - df[PortfolioColumns.EOD_CF.value]).to_numpy()
        if metric_basis == "NET":
            numerator += df[PortfolioColumns.MGMT_FEES.value].to_numpy()
        denominator = np.abs(df[PortfolioColumns.BEGIN_MV.value] + df[PortfolioColumns.BOD_CF.value]).to_numpy()
        local_ror = np.full(denominator.shape, 0.0, dtype=np.float64)

    is_after_start = df[PortfolioColumns.PERF_DATE.value] >= df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE.value]
    safe_division_mask = (denominator != zero) & is_after_start

    if is_decimal_mode:
        if safe_division_mask.any():
            local_ror.loc[safe_division_mask] = numerator[safe_division_mask] / denominator[safe_division_mask]
    else:
        np.divide(numerator, denominator, out=local_ror, where=safe_division_mask)

    # --- 2. Handle FX Decomposition if Activated ---
    result_df = pd.DataFrame(index=df.index)
    if config and config.currency_mode and config.currency_mode != "BASE_ONLY" and config.fx:
        fx_rates_df = pd.DataFrame([rate.model_dump() for rate in config.fx.rates])
        fx_rates_df['date'] = pd.to_datetime(fx_rates_df['date'])
        fx_rates_df = fx_rates_df.set_index('date')['rate'].sort_index()

        # Get prior day's FX rate for each performance date
        merged_df = pd.merge_asof(
            df[[PortfolioColumns.PERF_DATE.value]].sort_values(by=PortfolioColumns.PERF_DATE.value),
            fx_rates_df.rename('end_rate'),
            left_on=PortfolioColumns.PERF_DATE.value,
            right_index=True,
            direction='forward'
        )
        merged_df = pd.merge_asof(
            merged_df,
            fx_rates_df.rename('start_rate'),
            left_on=PortfolioColumns.PERF_DATE.value,
            right_index=True,
            direction='backward'
        )
        merged_df = merged_df.set_index(PortfolioColumns.PERF_DATE.value)

        # Calculate FX return
        fx_ror = (merged_df['end_rate'] / merged_df['start_rate']) - 1
        fx_ror = fx_ror.fillna(0.0)

        result_df["local_ror"] = local_ror * hundred
        result_df["fx_ror"] = fx_ror * hundred
        result_df[PortfolioColumns.DAILY_ROR.value] = ((1 + local_ror) * (1 + fx_ror) - 1) * hundred
    else:
        # Standard base-currency-only calculation
        result_df[PortfolioColumns.DAILY_ROR.value] = local_ror * hundred

    return result_df


def calculate_cumulative_ror(df: pd.DataFrame, config):
    """Orchestrates all cumulative return calculations, supporting both float and Decimal."""
    is_decimal_mode = df[PortfolioColumns.DAILY_ROR.value].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0
    hundred = Decimal(100) if is_decimal_mode else 100.0
    one = Decimal(1) if is_decimal_mode else 1.0

    df[PortfolioColumns.TEMP_LONG_CUM_ROR.value] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR.value], "long", use_resets=False)
    df[PortfolioColumns.TEMP_SHORT_CUM_ROR.value] = _compound_ror(df, df[PortfolioColumns.DAILY_ROR.value], "short", use_resets=False)

    report_end_ts = pd.to_datetime(config.report_end_date)
    initial_resets = calculate_initial_resets(df, report_end_ts)
    df[PortfolioColumns.PERF_RESET.value] = initial_resets.astype(int)

    final_long_ror = _compound_ror(df, df[PortfolioColumns.DAILY_ROR.value], "long", use_resets=True)
    final_short_ror = _compound_ror(df, df[PortfolioColumns.DAILY_ROR.value], "short", use_resets=True)

    df[PortfolioColumns.LONG_CUM_ROR.value] = final_long_ror
    df[PortfolioColumns.SHORT_CUM_ROR.value] = final_short_ror
    is_initial_reset_day = df[PortfolioColumns.PERF_RESET.value] == 1
    df.loc[is_initial_reset_day, [PortfolioColumns.LONG_CUM_ROR.value, PortfolioColumns.SHORT_CUM_ROR.value]] = zero

    nctrl4_resets = calculate_nctrl4_reset(df)
    df[PortfolioColumns.PERF_RESET.value] |= nctrl4_resets
    is_final_reset_day = df[PortfolioColumns.PERF_RESET.value] == 1
    df.loc[is_final_reset_day, [PortfolioColumns.LONG_CUM_ROR.value, PortfolioColumns.SHORT_CUM_ROR.value]] = zero

    df[PortfolioColumns.TEMP_LONG_CUM_ROR.value] = final_long_ror
    df[PortfolioColumns.TEMP_SHORT_CUM_ROR.value] = final_short_ror

    is_nip = df[PortfolioColumns.NIP.value] == 1
    df.loc[is_nip, [PortfolioColumns.LONG_CUM_ROR.value, PortfolioColumns.SHORT_CUM_ROR.value]] = np.nan
    df[[PortfolioColumns.LONG_CUM_ROR.value, PortfolioColumns.SHORT_CUM_ROR.value]] = df[
        [PortfolioColumns.LONG_CUM_ROR.value, PortfolioColumns.SHORT_CUM_ROR.value]
    ].ffill().fillna(zero)

    df[PortfolioColumns.FINAL_CUM_ROR.value] = (
        (one + df[PortfolioColumns.LONG_CUM_ROR.value] / hundred)
        * (one + df[PortfolioColumns.SHORT_CUM_ROR.value] / hundred)
        - one
    ) * hundred


def _compound_ror(df: pd.DataFrame, daily_ror: pd.Series, leg: str, use_resets=False) -> pd.Series:
    """Helper for geometric compounding, supporting both float and Decimal."""
    is_decimal_mode = daily_ror.dtype == "object"
    one = Decimal(1) if is_decimal_mode else 1.0
    hundred = Decimal(100) if is_decimal_mode else 100.0
    zero = Decimal(0) if is_decimal_mode else 0.0

    sign = df[PortfolioColumns.SIGN.value]
    if leg == "long":
        is_leg_day = sign == 1
        growth_factor = one + (daily_ror / hundred)
    else:
        is_leg_day = sign == -1
        growth_factor = one - (daily_ror / hundred)
    growth_factor = growth_factor.where(is_leg_day, one)

    is_period_start = df[PortfolioColumns.PERF_DATE.value] == df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE.value]
    block_starts = is_period_start
    if use_resets:
        prev_day_was_reset = df[PortfolioColumns.PERF_RESET.value].shift(1, fill_value=0) == 1
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