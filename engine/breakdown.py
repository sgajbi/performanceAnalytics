# engine/breakdown.py
from typing import Dict, List

import pandas as pd
from common.enums import Frequency
from core.annualize import annualize_return
from core.envelope import Annualization
from engine.schema import PortfolioColumns


def _calculate_period_summary_dict(
    period_df: pd.DataFrame, full_history_df: pd.DataFrame, annualization: Annualization, include_cumulative: bool
) -> Dict:
    """Calculates an aggregated summary dict for a given period DataFrame."""
    first_day = period_df.iloc[0]
    last_day = period_df.iloc[-1]

    period_ror = (1 + period_df[PortfolioColumns.DAILY_ROR.value] / 100).prod() - 1

    summary = {
        PortfolioColumns.BEGIN_MV.value: first_day[PortfolioColumns.BEGIN_MV.value],
        PortfolioColumns.END_MV.value: last_day[PortfolioColumns.END_MV.value],
        "net_cash_flow": (period_df[PortfolioColumns.BOD_CF.value] + period_df[PortfolioColumns.EOD_CF.value]).sum(),
        "period_return_pct": period_ror * 100,
    }

    if include_cumulative:
        # --- FIX START: Correctly calculate the period's specific cumulative return ---
        end_cum_ror = last_day[PortfolioColumns.FINAL_CUM_ROR.value]
        
        # Find the cumulative return from the day before this period started
        period_start_date = period_df[PortfolioColumns.PERF_DATE.value].iloc[0]
        day_before_mask = full_history_df[PortfolioColumns.PERF_DATE.value] < period_start_date
        
        start_cum_ror = 0.0
        if day_before_mask.any():
            day_before_row = full_history_df[day_before_mask].iloc[-1]
            start_cum_ror = day_before_row[PortfolioColumns.FINAL_CUM_ROR.value]
            
        period_cumulative_ror = (((1 + end_cum_ror / 100) / (1 + start_cum_ror / 100)) - 1) * 100
        summary["cumulative_return_pct_to_date"] = period_cumulative_ror
        # --- FIX END ---

    if annualization.enabled:
        days_in_period = (period_df.index.max() - period_df.index.min()).days + 1
        ppy = annualization.periods_per_year or (252 if annualization.basis == "BUS/252" else 365.0)
        
        if days_in_period >= ppy:
            summary["annualized_return_pct"] = (
                annualize_return(period_ror, days_in_period, ppy, annualization.basis) * 100
            )
    return summary


def generate_performance_breakdowns(
    daily_df: pd.DataFrame,
    frequencies: List[Frequency],
    annualization: Annualization,
    include_cumulative: bool,
) -> Dict[Frequency, List[Dict]]:
    """
    Takes a DataFrame of daily performance data and aggregates it into
    the requested frequencies, returning pure Python objects.
    """
    if daily_df.empty:
        return {}

    daily_df_indexed = daily_df.set_index(pd.to_datetime(daily_df[PortfolioColumns.PERF_DATE.value]))
    breakdowns = {}

    for freq in frequencies:
        results = []
        if freq == Frequency.DAILY:
            for i, row in daily_df.iterrows():
                # --- FIX START: Correctly calculate daily cumulative return ---
                if include_cumulative:
                    day_before_mask = daily_df[PortfolioColumns.PERF_DATE.value] < row[PortfolioColumns.PERF_DATE.value]
                    start_cum_ror = daily_df[day_before_mask].iloc[-1][PortfolioColumns.FINAL_CUM_ROR.value] if day_before_mask.any() else 0.0
                    end_cum_ror = row[PortfolioColumns.FINAL_CUM_ROR.value]
                    cumulative_return = (((1 + end_cum_ror / 100) / (1 + start_cum_ror / 100)) - 1) * 100
                # --- FIX END ---
                summary = {
                    PortfolioColumns.BEGIN_MV.value: row[PortfolioColumns.BEGIN_MV.value],
                    PortfolioColumns.END_MV.value: row[PortfolioColumns.END_MV.value],
                    "net_cash_flow": row[PortfolioColumns.BOD_CF.value] + row[PortfolioColumns.EOD_CF.value],
                    "period_return_pct": row[PortfolioColumns.DAILY_ROR.value],
                }
                if include_cumulative:
                    summary["cumulative_return_pct_to_date"] = cumulative_return
                results.append({"period": row[PortfolioColumns.PERF_DATE.value].strftime("%Y-%m-%d"), "summary": summary})
        else:
            freq_map = {Frequency.MONTHLY: "ME", Frequency.QUARTERLY: "QE", Frequency.YEARLY: "YE", Frequency.WEEKLY: "W-FRI"}
            resampler = daily_df_indexed.resample(freq_map[freq])
            for period_timestamp, period_df in resampler:
                if period_df.empty:
                    continue
                # For aggregated periods, we pass the full daily_df for the prior-day lookup
                summary = _calculate_period_summary_dict(
                    period_df, daily_df, annualization, include_cumulative
                )
                if freq == Frequency.MONTHLY:
                    period_str = period_timestamp.strftime("%Y-%m")
                elif freq == Frequency.QUARTERLY:
                    period_str = f"{period_timestamp.year}-Q{period_timestamp.quarter}"
                elif freq == Frequency.YEARLY:
                    period_str = period_timestamp.strftime("%Y")
                else:  # Weekly
                    period_str = period_timestamp.strftime("%Y-%m-%d")
                results.append({"period": period_str, "summary": summary})
        breakdowns[freq] = results
    return breakdowns