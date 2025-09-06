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

    period_ror = (1 + period_df[PortfolioColumns.DAILY_ROR] / 100).prod() - 1

    summary = {
        PortfolioColumns.BEGIN_MV: first_day[PortfolioColumns.BEGIN_MV],
        PortfolioColumns.END_MV: last_day[PortfolioColumns.END_MV],
        "net_cash_flow": (period_df[PortfolioColumns.BOD_CF] + period_df[PortfolioColumns.EOD_CF]).sum(),
        "period_return_pct": period_ror * 100,
    }

    if include_cumulative:
        summary["cumulative_return_pct_to_date"] = last_day[PortfolioColumns.FINAL_CUM_ROR]

    if annualization.enabled:
        ppy = annualization.periods_per_year or (252 if annualization.basis == "BUS/252" else 365.25)
        summary["annualized_return_pct"] = (
            annualize_return(period_ror, len(period_df), ppy, annualization.basis) * 100
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

    daily_df_indexed = daily_df.set_index(pd.to_datetime(daily_df[PortfolioColumns.PERF_DATE]))
    breakdowns = {}

    for freq in frequencies:
        results = []
        if freq == Frequency.DAILY:
            for _, row in daily_df.iterrows():
                summary = {
                    PortfolioColumns.BEGIN_MV: row[PortfolioColumns.BEGIN_MV],
                    PortfolioColumns.END_MV: row[PortfolioColumns.END_MV],
                    "net_cash_flow": row[PortfolioColumns.BOD_CF] + row[PortfolioColumns.EOD_CF],
                    "period_return_pct": row[PortfolioColumns.DAILY_ROR],
                }
                if include_cumulative:
                    summary["cumulative_return_pct_to_date"] = row[PortfolioColumns.FINAL_CUM_ROR]
                results.append({"period": row[PortfolioColumns.PERF_DATE].strftime("%Y-%m-%d"), "summary": summary})
        else:
            freq_map = {Frequency.MONTHLY: "ME", Frequency.QUARTERLY: "QE", Frequency.YEARLY: "YE", Frequency.WEEKLY: "W-FRI"}
            resampler = daily_df_indexed.resample(freq_map[freq])
            for period_timestamp, period_df in resampler:
                if period_df.empty:
                    continue
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