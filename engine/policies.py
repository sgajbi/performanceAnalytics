# engine/policies.py
import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.models.requests import DataPolicy
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
        mask = (df_copy[PortfolioColumns.PERF_DATE.value] == pd.to_datetime(override["perf_date"]))
        # In a multi-position context, we would also filter by position_id
        if "position_id" in override:
             if "position_id" in df_copy.columns:
                mask &= (df_copy["position_id"] == override["position_id"])

        if not df_copy.loc[mask].empty:
            for key in ["begin_mv", "end_mv"]:
                if key in override:
                    df_copy.loc[mask, key] = override[key]
                    diagnostics["policy"]["overrides"]["applied_mv_count"] += 1

    for override in cf_overrides:
        mask = (df_copy[PortfolioColumns.PERF_DATE.value] == pd.to_datetime(override["perf_date"]))
        if not df_copy.loc[mask].empty:
            for key in ["bod_cf", "eod_cf"]:
                if key in override:
                    df_copy.loc[mask, key] = override[key]
                    diagnostics["policy"]["overrides"]["applied_cf_count"] += 1

    if diagnostics["policy"]["overrides"]["applied_mv_count"] > 0 or diagnostics["policy"]["overrides"]["applied_cf_count"] > 0:
        diagnostics["notes"].append("Applied overrides from the data_policy request.")

    return df_copy


def _apply_ignore_days(df: pd.DataFrame, ignore_days: list, diagnostics: Dict) -> pd.DataFrame:
    """Applies policy to ignore specified days by carrying forward previous day's state."""
    if not ignore_days:
        return df

    df_copy = df.copy()
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
        diagnostics["notes"].append(f"Ignored {diagnostics['policy']['ignored_days_count']} day(s) as specified in data_policy.")

    return df_copy.reset_index()


def _flag_outliers(df: pd.DataFrame, outlier_policy: Dict, diagnostics: Dict) -> None:
    """Detects and flags outliers without modifying data."""
    if not outlier_policy or not outlier_policy.get("enabled"):
        return

    if outlier_policy["action"] != "FLAG":
        return  # Only flagging is supported

    window = outlier_policy.get("params", {}).get("window", 63)
    mad_k = outlier_policy.get("params", {}).get("mad_k", 5.0)

    # This requires daily_ror to be calculated first.
    # We will flag them and add to diagnostics.
    if PortfolioColumns.DAILY_ROR.value not in df.columns:
        return

    ror_series = df[PortfolioColumns.DAILY_ROR.value]
    median = ror_series.rolling(window=window, min_periods=1).median()
    mad = (ror_series - median).abs().rolling(window=window, min_periods=1).median()
    
    # Avoid division by zero if MAD is 0
    mad = mad.replace(0, np.nan).ffill().fillna(1e-9)

    upper_bound = median + mad_k * mad
    lower_bound = median - mad_k * mad

    outliers = (ror_series > upper_bound) | (ror_series < lower_bound)
    diagnostics["policy"]["outliers"]["flagged_rows"] = int(outliers.sum())

    if int(outliers.sum()) > 0:
        sample = df[outliers].iloc[0]
        diagnostics["samples"]["outliers"].append(
            {
                "date": sample[PortfolioColumns.PERF_DATE.value].strftime("%Y-%m-%d"),
                "raw_return": sample[PortfolioColumns.DAILY_ROR.value],
                "threshold": upper_bound[outliers].iloc[0]
            }
        )


def apply_robustness_policies(
    df: pd.DataFrame, data_policy_model: BaseModel | None
) -> Tuple[pd.DataFrame, Dict]:
    """Orchestrator to apply all robustness policies in the correct order."""
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

    # Convert Pydantic model to dict for easier processing
    data_policy = data_policy_model.model_dump(exclude_unset=True)
    
    # 1. Apply Overrides and Ignore Days first as they modify the base data
    df = _apply_overrides(df, data_policy.get("overrides"), diagnostics)
    df = _apply_ignore_days(df, data_policy.get("ignore_days"), diagnostics)

    # Outlier flagging would happen after daily_ror is calculated, so we only
    # return the diagnostics structure for the orchestrator to use later.
    return df, diagnostics