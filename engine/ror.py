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
    """
    is_decimal_mode = df[PortfolioColumns.BEGIN_MV.value].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0
    hundred = Decimal(100) if is_decimal_mode else 100.0

    if is_decimal_mode:
        numerator = (
            df[PortfolioColumns.END_MV.value]
            - df[PortfolioColumns.BOD_CF.value]
            - df[PortfolioColumns.BEGIN_MV.value]
            - df[PortfolioColumns.EOD_CF.value]
        )
        if metric_basis == "NET":
            numerator += df[PortfolioColumns.MGMT_FEES.value]
        denominator = (df[PortfolioColumns.BEGIN_MV.value] + df[PortfolioColumns.BOD_CF.value]).abs()
        local_ror = pd.Series([zero] * len(df), index=df.index, dtype=object)
    else:
        numerator = (
            df[PortfolioColumns.END_MV.value]
            - df[PortfolioColumns.BOD_CF.value]
            - df[PortfolioColumns.BEGIN_MV.value]
            - df[PortfolioColumns.EOD_CF.value]
        ).to_numpy(copy=True)
        if metric_basis == "NET":
            numerator += df[PortfolioColumns.MGMT_FEES.value].to_numpy(copy=False)
        denominator = np.abs(df[PortfolioColumns.BEGIN_MV.value] + df[PortfolioColumns.BOD_CF.value]).to_numpy(
            copy=False
        )
        local_ror_np = np.full(denominator.shape, 0.0, dtype=np.float64)

    is_after_start = df[PortfolioColumns.PERF_DATE.value] >= df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE.value]
    safe_division_mask = (denominator != zero) & is_after_start

    with np.errstate(divide="ignore", invalid="ignore"):
        if is_decimal_mode:
            if safe_division_mask.any():
                local_ror.loc[safe_division_mask] = numerator[safe_division_mask] / denominator[safe_division_mask]
        else:
            np.divide(numerator, denominator, out=local_ror_np, where=safe_division_mask)
            local_ror = pd.Series(local_ror_np, index=df.index)

    result_df = pd.DataFrame(index=df.index)
    if config and config.currency_mode and config.currency_mode != "BASE_ONLY" and config.fx:
        fx_rates_df = pd.DataFrame([rate.model_dump() for rate in config.fx.rates])

        if "date" in fx_rates_df.columns and "ccy" in fx_rates_df.columns:
            fx_rates_df.drop_duplicates(subset=["date", "ccy"], keep="last", inplace=True)

        fx_rates_df["date"] = pd.to_datetime(fx_rates_df["date"])
        fx_rates_df = fx_rates_df.set_index("date")["rate"].sort_index()

        start_dt = pd.to_datetime(config.performance_start_date) - pd.Timedelta(days=1)
        end_dt = df[PortfolioColumns.PERF_DATE.value].max()
        full_date_range = pd.date_range(start=start_dt, end=end_dt, freq="D")
        all_rates = fx_rates_df.reindex(full_date_range).ffill()

        df["start_rate"] = df[PortfolioColumns.PERF_DATE.value].apply(lambda x: all_rates.get(x - pd.Timedelta(days=1)))
        df["end_rate"] = df[PortfolioColumns.PERF_DATE.value].map(all_rates)

        fx_ror = (df["end_rate"] / df["start_rate"]) - 1
        fx_ror = fx_ror.fillna(0.0)

        if config.hedging and config.hedging.mode == "RATIO" and config.hedging.series:
            hedge_series_df = pd.DataFrame([s.model_dump() for s in config.hedging.series])
            if not hedge_series_df.empty:
                hedge_series_df["date"] = pd.to_datetime(hedge_series_df["date"])
                hedge_map = hedge_series_df.set_index("date")["hedge_ratio"]
                hedge_ratios = df[PortfolioColumns.PERF_DATE.value].map(hedge_map).fillna(0.0)
                fx_ror = fx_ror * (1.0 - hedge_ratios)

        result_df["local_ror"] = local_ror * hundred
        result_df["fx_ror"] = fx_ror * hundred
        result_df[PortfolioColumns.DAILY_ROR.value] = ((1 + local_ror) * (1 + fx_ror) - 1) * hundred
    else:
        result_df[PortfolioColumns.DAILY_ROR.value] = local_ror * hundred

    return result_df


def calculate_cumulative_ror(df: pd.DataFrame, config):
    """Orchestrates all cumulative return calculations, supporting both float and Decimal."""
    is_decimal_mode = df[PortfolioColumns.DAILY_ROR.value].dtype == "object"
    one = Decimal(1) if is_decimal_mode else 1.0
    hundred = Decimal(100) if is_decimal_mode else 100.0

    # --- START FIX: Ensure base calculation is done first and separately ---
    base_components = [PortfolioColumns.DAILY_ROR.value]
    other_components = []
    if "local_ror" in df.columns:
        other_components.append("local_ror")
    if "fx_ror" in df.columns:
        other_components.append("fx_ror")

    # Step 1: Calculate temp cumulative returns for all components (pre-reset)
    for component_name in base_components + other_components:
        prefix = f"{component_name}_" if component_name != PortfolioColumns.DAILY_ROR.value else ""
        df[f"temp_{prefix}long_cum_ror"] = _compound_ror(df, df[component_name], "long", use_resets=False)
        df[f"temp_{prefix}short_cum_ror"] = _compound_ror(df, df[component_name], "short", use_resets=False)

    # Step 2: Determine resets based ONLY on the base TWR
    initial_resets, nctrl1, nctrl2, nctrl3 = calculate_initial_resets(
        df,
        pd.to_datetime(config.report_end_date),
        PortfolioColumns.TEMP_LONG_CUM_ROR.value,
        PortfolioColumns.TEMP_SHORT_CUM_ROR.value,
    )
    df[PortfolioColumns.NCTRL_1.value] = nctrl1.astype(int)
    df[PortfolioColumns.NCTRL_2.value] = nctrl2.astype(int)
    df[PortfolioColumns.NCTRL_3.value] = nctrl3.astype(int)
    df[PortfolioColumns.PERF_RESET.value] = initial_resets.astype(int)

    # Step 3: Recalculate all cumulative returns applying the same reset logic
    for component_name in base_components + other_components:
        prefix = f"{component_name}_" if component_name != PortfolioColumns.DAILY_ROR.value else ""
        df[f"{prefix}long_cum_ror"] = _compound_ror(df, df[component_name], "long", use_resets=True)
        df[f"{prefix}short_cum_ror"] = _compound_ror(df, df[component_name], "short", use_resets=True)

    is_initial_reset_day = df[PortfolioColumns.PERF_RESET.value] == 1
    for component_name in base_components + other_components:
        prefix = f"{component_name}_" if component_name != PortfolioColumns.DAILY_ROR.value else ""
        df.loc[is_initial_reset_day, [f"{prefix}long_cum_ror", f"{prefix}short_cum_ror"]] = 0.0

    # Step 4: Final reset calculations based on base TWR
    nctrl4_resets = calculate_nctrl4_reset(
        df,
        long_cum_col=PortfolioColumns.LONG_CUM_ROR.value,
        short_cum_col=PortfolioColumns.SHORT_CUM_ROR.value,
    )
    df[PortfolioColumns.NCTRL_4.value] = nctrl4_resets.astype(int)
    df.loc[nctrl4_resets, PortfolioColumns.PERF_RESET.value] = 1  # Use .loc to update

    is_final_reset_day = df[PortfolioColumns.PERF_RESET.value] == 1
    for component_name in base_components + other_components:
        prefix = f"{component_name}_" if component_name != PortfolioColumns.DAILY_ROR.value else ""
        df.loc[is_final_reset_day, [f"{prefix}long_cum_ror", f"{prefix}short_cum_ror"]] = 0.0

    # Step 5: Handle NIP days for all components
    is_nip = df[PortfolioColumns.NIP.value] == 1
    for component_name in base_components + other_components:
        prefix = f"{component_name}_" if component_name != PortfolioColumns.DAILY_ROR.value else ""
        df.loc[is_nip, [f"{prefix}long_cum_ror", f"{prefix}short_cum_ror"]] = np.nan
        df[[f"{prefix}long_cum_ror", f"{prefix}short_cum_ror"]] = (
            df[[f"{prefix}long_cum_ror", f"{prefix}short_cum_ror"]].ffill().fillna(0.0)
        )

    # Step 6: Calculate the final cumulative return based ONLY on the base components
    df[PortfolioColumns.FINAL_CUM_ROR.value] = (
        (one + df[PortfolioColumns.LONG_CUM_ROR.value] / hundred)
        * (one + df[PortfolioColumns.SHORT_CUM_ROR.value] / hundred)
        - one
    ) * hundred
    # --- END FIX ---


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

    prev_eff_start = df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE.value].shift(1)
    is_period_start = df[PortfolioColumns.EFFECTIVE_PERIOD_START_DATE.value] != prev_eff_start
    if not df.empty:
        is_period_start.iloc[0] = True

    block_starts = is_period_start
    if use_resets:
        prev_day_was_reset = df[PortfolioColumns.PERF_RESET.value].shift(1, fill_value=0) == 1
        block_starts |= prev_day_was_reset
    block_ids = block_starts.cumsum()

    if is_decimal_mode:

        def decimal_cumprod(series):
            result = series.copy()
            for i in range(1, len(series)):
                result.iloc[i] = result.iloc[i - 1] * result.iloc[i]
            return result

        cumulative_growth = growth_factor.groupby(block_ids, group_keys=False).apply(decimal_cumprod)
    else:
        cumulative_growth = growth_factor.groupby(block_ids).cumprod()

    cumulative_ror = (cumulative_growth - one) * hundred
    if leg == "short":
        cumulative_ror *= -one
    leg_ror = cumulative_ror.where(is_leg_day)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        filled_ror = leg_ror.ffill().fillna(zero)

    return filled_ror
