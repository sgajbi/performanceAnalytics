# engine/breakdown.py
from typing import Dict, List

import pandas as pd
from common.enums import Frequency
from app.models.responses import PerformanceResultItem, PerformanceSummary
from engine.schema import PortfolioColumns


def _calculate_period_summary_dict(period_df: pd.DataFrame) -> Dict:
    """Calculates an aggregated summary dict for a given period DataFrame."""
    first_day = period_df.iloc[0]
    last_day = period_df.iloc[-1]

    period_ror = (1 + period_df[PortfolioColumns.DAILY_ROR] / 100).prod() - 1

    return {
        PortfolioColumns.BEGIN_MV: first_day[PortfolioColumns.BEGIN_MV],
        PortfolioColumns.END_MV: last_day[PortfolioColumns.END_MV],
        "net_cash_flow": (period_df[PortfolioColumns.BOD_CF] + period_df[PortfolioColumns.EOD_CF]).sum(),
        PortfolioColumns.FINAL_CUM_ROR: period_ror * 100,
    }


def generate_performance_breakdowns(
    daily_df: pd.DataFrame, frequencies: List[Frequency]
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
                    PortfolioColumns.FINAL_CUM_ROR: row[PortfolioColumns.DAILY_ROR],
                }
                results.append({
                    "period": row[PortfolioColumns.PERF_DATE].strftime('%Y-%m-%d'),
                    "summary": summary
                })
        else:
            # FIX: Use modern pandas frequency codes to remove warnings
            freq_map = {
                Frequency.MONTHLY: "ME",
                Frequency.QUARTERLY: "QE",
                Frequency.YEARLY: "YE",
            }
            resampler = daily_df_indexed.resample(freq_map[freq])
            for period_timestamp, period_df in resampler:
                if period_df.empty:
                    continue
                summary = _calculate_period_summary_dict(period_df)
                if freq == Frequency.MONTHLY:
                    period_str = period_timestamp.strftime('%Y-%m')
                elif freq == Frequency.QUARTERLY:
                    period_str = f"{period_timestamp.year}-Q{period_timestamp.quarter}"
                elif freq == Frequency.YEARLY:
                    period_str = period_timestamp.strftime('%Y')
                results.append({"period": period_str, "summary": summary})
        breakdowns[freq] = results
    return breakdowns