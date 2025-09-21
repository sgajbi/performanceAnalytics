# engine/breakdown.py
from typing import Dict, List

import pandas as pd
from common.enums import Frequency
from core.annualize import annualize_return
from core.envelope import Annualization
from engine.schema import PortfolioColumns


def _calculate_period_summary_dict(
    period_df: pd.DataFrame, full_history_df: pd.DataFrame, annualization: Annualization, include_cumulative: bool, rounding_precision: int
) -> Dict:
    """Calculates an aggregated summary dict for a given period DataFrame."""
    first_day = period_df.iloc[0]
    last_day = period_df.iloc[-1]

    # --- START FIX: Use base return for period summary, not just local ---
    period_ror = (1 + period_df[PortfolioColumns.DAILY_ROR.value] / 100).prod() - 1
    # --- END FIX ---

    summary = {
        PortfolioColumns.BEGIN_MV.value: first_day[PortfolioColumns.BEGIN_MV.value],
        PortfolioColumns.END_MV.value: last_day[PortfolioColumns.END_MV.value],
        "net_cash_flow": (period_df[PortfolioColumns.BOD_CF.value] + period_df[PortfolioColumns.EOD_CF.value]).sum(),
        "period_return_pct": round(period_ror * 100, rounding_precision),
    }

    if include_cumulative:
        summary["cumulative_return_pct_to_date"] = round(last_day[PortfolioColumns.FINAL_CUM_ROR.value], rounding_precision)

    if annualization.enabled:
        # --- START FIX: Use correct number of calendar days for annualization factor ---
        days_in_period = (last_day[PortfolioColumns.PERF_DATE] - first_day[PortfolioColumns.PERF_DATE]).days + 1
        ppy = annualization.periods_per_year or (252 if annualization.basis == "BUS/252" else 365.25 if annualization.basis == "ACT/ACT" else 365.0)
        
        # Only show annualized return for periods shorter than a year as per convention
        if days_in_period > 0 and days_in_period < (ppy + 1):
            annualized_return = annualize_return(period_ror, days_in_period, ppy, annualization.basis) * 100
            summary["annualized_return_pct"] = round(annualized_return, rounding_precision)
        # --- END FIX ---

    return summary


def generate_performance_breakdowns(
    daily_df: pd.DataFrame,
    frequencies: List[Frequency],
    annualization: Annualization,
    include_cumulative: bool,
    rounding_precision: int = 6,
) -> Dict[Frequency, List[Dict]]:
    """
    Takes a DataFrame of daily performance data and aggregates it into
    the requested frequencies, returning pure Python objects.
    """
    if daily_df.empty:
        return {}
    
    # --- START FIX: Ensure daily_df has a proper date column for joins ---
    daily_df[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(daily_df[PortfolioColumns.PERF_DATE.value])
    # --- END FIX ---
    daily_df_indexed = daily_df.set_index(pd.to_datetime(daily_df[PortfolioColumns.PERF_DATE.value]))

    breakdowns = {}

    for freq in frequencies:
        results = []
        if freq == Frequency.DAILY:
            for _, row in daily_df.iterrows():
                summary = {
                    PortfolioColumns.BEGIN_MV.value: row[PortfolioColumns.BEGIN_MV.value],
                    PortfolioColumns.END_MV.value: row[PortfolioColumns.END_MV.value],
                    "net_cash_flow": row[PortfolioColumns.BOD_CF.value] + row[PortfolioColumns.EOD_CF.value],
                    "period_return_pct": row[PortfolioColumns.DAILY_ROR.value],
                }
                if include_cumulative:
                    summary["cumulative_return_pct_to_date"] = row[PortfolioColumns.FINAL_CUM_ROR.value]
                
                results.append({"period": row[PortfolioColumns.PERF_DATE.value].strftime("%Y-%m-%d"), "summary": summary})
        else:
            freq_map = {Frequency.MONTHLY: "ME", Frequency.QUARTERLY: "QE", Frequency.YEARLY: "YE", Frequency.WEEKLY: "W-FRI"}
            resampler = daily_df_indexed.resample(freq_map[freq])
            for period_timestamp, period_df in resampler:
                if period_df.empty:
                    continue
                # --- START FIX: Pass the original full dataframe for history context ---
                summary = _calculate_period_summary_dict(
                    period_df, daily_df, annualization, include_cumulative, rounding_precision
                )
                # --- END FIX ---
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