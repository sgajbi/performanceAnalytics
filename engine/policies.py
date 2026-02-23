# engine/policies.py
import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from engine.schema import PortfolioColumns

logger = logging.getLogger(__name__)


def _apply_overrides(df: pd.DataFrame, overrides: Dict, diagnostics: Dict) -> pd.DataFrame:
    """Applies user-provided market value and cash flow overrides in-memory."""
    if not overrides:
        return df

    df_copy = df.copy()
    mv_overrides = overrides.get("market_values", [])
    cf_overrides = overrides.get("cash_flows", [])

    for override in mv_overrides:
        mask = df_copy[PortfolioColumns.PERF_DATE.value] == pd.to_datetime(override["perf_date"])
        # In a multi-position context, we would also filter by position_id
        if "position_id" in override:
            if "position_id" in df_copy.columns:
                mask &= df_copy["position_id"] == override["position_id"]

        if not df_copy.loc[mask].empty:
            for key in ["begin_mv", "end_mv"]:
                if key in override:
                    df_copy.loc[mask, key] = override[key]
                    diagnostics["policy"]["overrides"]["applied_mv_count"] += 1

    for override in cf_overrides:
        mask = df_copy[PortfolioColumns.PERF_DATE.value] == pd.to_datetime(override["perf_date"])
        if not df_copy.loc[mask].empty:
            for key in ["bod_cf", "eod_cf"]:
                if key in override:
                    df_copy.loc[mask, key] = override[key]
                    diagnostics["policy"]["overrides"]["applied_cf_count"] += 1

    if (
        diagnostics["policy"]["overrides"]["applied_mv_count"] > 0
        or diagnostics["policy"]["overrides"]["applied_cf_count"] > 0
    ):
        diagnostics["notes"].append("Applied overrides from the data_policy request.")

    return df_copy


def _apply_ignore_days(df: pd.DataFrame, ignore_days: list, diagnostics: Dict) -> pd.DataFrame:
    """Applies policy to ignore specified days by carrying forward previous day's state."""
    if not ignore_days:
        return df

    df_copy = df.copy()
    # Ensure DataFrame is sorted by date for correct forward-fill logic
    df_copy.sort_values(by=PortfolioColumns.PERF_DATE.value, inplace=True)
    df_copy.set_index(PortfolioColumns.PERF_DATE.value, inplace=True)

    for item in ignore_days:
        dates_to_ignore = pd.to_datetime(item["dates"])
        for date in dates_to_ignore:
            if date in df_copy.index:
                loc = df_copy.index.get_loc(date)
                if loc > 0:
                    prev_day = df_copy.iloc[loc - 1]
                    df_copy.loc[date, PortfolioColumns.BEGIN_MV.value] = prev_day[PortfolioColumns.END_MV.value]
                    df_copy.loc[date, PortfolioColumns.END_MV.value] = prev_day[PortfolioColumns.END_MV.value]
                    df_copy.loc[date, PortfolioColumns.BOD_CF.value] = 0.0
                    df_copy.loc[date, PortfolioColumns.EOD_CF.value] = 0.0
                    df_copy.loc[date, PortfolioColumns.MGMT_FEES.value] = 0.0
                    diagnostics["policy"]["ignored_days_count"] += 1

    if diagnostics["policy"]["ignored_days_count"] > 0:
        diagnostics["notes"].append(
            f"Ignored {diagnostics['policy']['ignored_days_count']} day(s) as specified in data_policy."
        )

    return df_copy.reset_index()


def _flag_outliers(df: pd.DataFrame, data_policy_model: BaseModel | None, diagnostics: Dict) -> None:
    """Detects and flags outliers, excluding ignored days from statistical analysis."""
    if not data_policy_model or not data_policy_model.outliers or not data_policy_model.outliers.enabled:
        return

    outlier_policy = data_policy_model.outliers.model_dump()
    if outlier_policy.get("action") != "FLAG":
        return

    window = outlier_policy.get("params", {}).get("window", 63)
    mad_k = outlier_policy.get("params", {}).get("mad_k", 5.0)

    if PortfolioColumns.DAILY_ROR.value not in df.columns:
        return

    # Exclude ignored days from the statistical calculation
    ror_series = df[PortfolioColumns.DAILY_ROR.value]
    ror_for_stats = ror_series.copy()
    if data_policy_model.ignore_days:
        ignored_dates = {d for item in data_policy_model.ignore_days for d in item.dates}
        valid_mask = ~df[PortfolioColumns.PERF_DATE.value].dt.date.isin(ignored_dates)
        ror_for_stats = ror_for_stats.where(valid_mask)  # Use .where to keep index alignment

    median = ror_for_stats.rolling(window=window, min_periods=1).median().ffill()
    mad = (ror_for_stats - median).abs().rolling(window=window, min_periods=1).median().ffill()

    mad.replace(0, np.nan, inplace=True)
    mad.ffill(inplace=True)
    mad.fillna(1e-9, inplace=True)

    upper_bound = median + mad_k * mad
    lower_bound = median - mad_k * mad

    # Flag outliers based on the original full series
    outliers = (ror_series > upper_bound) | (ror_series < lower_bound)
    # But only flag if the day was not ignored
    if data_policy_model.ignore_days:
        outliers &= valid_mask

    diagnostics["policy"]["outliers"]["flagged_rows"] = int(outliers.sum())

    if int(outliers.sum()) > 0:
        outlier_indices = df.index[outliers]
        for index in outlier_indices:
            sample = df.loc[index]
            diagnostics["samples"]["outliers"].append(
                {
                    "date": sample[PortfolioColumns.PERF_DATE.value].strftime("%Y-%m-%d"),
                    "raw_return": sample[PortfolioColumns.DAILY_ROR.value],
                    "threshold": upper_bound[index] if ror_series[index] > 0 else lower_bound[index],
                }
            )


def apply_robustness_policies(df: pd.DataFrame, data_policy_model: BaseModel | None) -> Tuple[pd.DataFrame, Dict]:
    """Orchestrator to apply pre-calculation robustness policies."""
    diagnostics = {
        "policy": {
            "overrides": {"applied_mv_count": 0, "applied_cf_count": 0},
            "ignored_days_count": 0,
            "outliers": {"flagged_rows": 0},
        },
        "samples": {"outliers": []},
        "notes": [],
    }

    if not data_policy_model:
        return df, diagnostics

    # These policies modify the base data before RoR calculation
    df = _apply_overrides(df, data_policy_model.model_dump(exclude_unset=True).get("overrides"), diagnostics)
    df = _apply_ignore_days(df, data_policy_model.model_dump(exclude_unset=True).get("ignore_days"), diagnostics)

    return df, diagnostics
