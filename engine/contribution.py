# engine/contribution.py
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from app.models.contribution_requests import ContributionRequest, Emit, Smoothing
from common.enums import WeightingScheme
from engine.schema import PortfolioColumns
from engine.compute import run_calculations
from engine.config import EngineConfig
from adapters.api_adapter import create_engine_dataframe


def _calculate_daily_instrument_contributions(
    instruments_df: pd.DataFrame, portfolio_df: pd.DataFrame, weighting_scheme: WeightingScheme, smoothing: Smoothing
) -> pd.DataFrame:
    """
    Calculates daily weights and smoothed contributions for each instrument.
    """
    if instruments_df.empty:
        return instruments_df

    # Merge portfolio totals needed for weight calculation
    df = pd.merge(
        instruments_df,
        portfolio_df[[PortfolioColumns.PERF_DATE.value, PortfolioColumns.BEGIN_MV.value, PortfolioColumns.BOD_CF.value]],
        on=PortfolioColumns.PERF_DATE.value,
        suffixes=("", "_port"),
    )

    # 1. Calculate Daily Weights based on the selected scheme
    if weighting_scheme == WeightingScheme.BOD:
        df["capital_inst"] = df[PortfolioColumns.BEGIN_MV.value] + df[PortfolioColumns.BOD_CF.value]
        df["capital_port"] = df[f"{PortfolioColumns.BEGIN_MV.value}_port"] + df[f"{PortfolioColumns.BOD_CF.value}_port"]
    # Add other weighting schemes here when implemented
    # elif weighting_scheme == WeightingScheme.AVG_CAPITAL: ...

    df["daily_weight"] = (df["capital_inst"] / df["capital_port"]).fillna(0.0)

    # 2. Calculate Raw Daily Contribution
    df["raw_contribution"] = df["daily_weight"] * (df[PortfolioColumns.DAILY_ROR.value] / 100)

    # 3. Apply Carino Smoothing if requested
    if smoothing.method == "CARINO":
        portfolio_df_indexed = portfolio_df.set_index(PortfolioColumns.PERF_DATE.value)
        port_ror_series = portfolio_df_indexed[PortfolioColumns.DAILY_ROR.value] / 100
        k_daily = _calculate_carino_factors(port_ror_series)
        port_total_ror = (1 + port_ror_series).prod() - 1
        K_total = (np.log(1 + port_total_ror) / port_total_ror if port_total_ror != 0 else 1.0)

        df = pd.merge(df, k_daily.rename("k_t"), left_on=PortfolioColumns.PERF_DATE.value, right_index=True)
        df["K_total"] = K_total

        # Carino formula: c'_p,t = c_p,t + (w_p,t * (R_port,t * (K/k_t - 1)))
        port_ror_daily_map = portfolio_df_indexed[PortfolioColumns.DAILY_ROR.value] / 100
        df["R_port_t"] = df[PortfolioColumns.PERF_DATE.value].map(port_ror_daily_map)
        adjustment_factor = df["daily_weight"] * (df["R_port_t"] * ((df["K_total"] / df["k_t"]) - 1))
        df["smoothed_contribution"] = df["raw_contribution"] + adjustment_factor.fillna(0.0)
    else:
        df["smoothed_contribution"] = df["raw_contribution"]

    # 4. Handle NIP and Reset days
    nip_reset_dates = portfolio_df[
        (portfolio_df[PortfolioColumns.NIP.value] == 1) | (portfolio_df[PortfolioColumns.PERF_RESET.value] == 1)
    ][PortfolioColumns.PERF_DATE.value]
    df.loc[df[PortfolioColumns.PERF_DATE.value].isin(nip_reset_dates), "smoothed_contribution"] = 0.0

    return df


def _prepare_hierarchical_data(request: ContributionRequest) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Runs TWR calculations and combines all position data and metadata into a single DataFrame.
    """
    # 1. Create a shared TWR config
    perf_start_date = request.portfolio_data.daily_data[0].perf_date
    twr_config = EngineConfig(
        performance_start_date=perf_start_date,
        report_start_date=request.portfolio_data.report_start_date,
        report_end_date=request.portfolio_data.report_end_date,
        metric_basis=request.portfolio_data.metric_basis,
        period_type=request.portfolio_data.period_type,
        precision_mode=request.precision_mode,
        rounding_precision=request.rounding_precision,
    )

    # 2. Calculate portfolio-level performance
    portfolio_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in request.portfolio_data.daily_data])
    portfolio_results_df, portfolio_diags = run_calculations(portfolio_df, twr_config)
    portfolio_results_df[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(portfolio_results_df[PortfolioColumns.PERF_DATE.value])

    # 3. Calculate performance for each position and combine with metadata
    all_positions_data = []
    for position in request.positions_data:
        position_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in position.daily_data])
        if position_df.empty:
            continue

        position_results_df, _ = run_calculations(position_df, twr_config)
        position_results_df[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(position_results_df[PortfolioColumns.PERF_DATE.value])
        position_results_df["position_id"] = position.position_id
        for key, value in position.meta.items():
            position_results_df[key] = value

        all_positions_data.append(position_results_df)

    if not all_positions_data:
        return pd.DataFrame(), portfolio_results_df

    instruments_df = pd.concat(all_positions_data, ignore_index=True)
    return instruments_df, portfolio_results_df


def calculate_hierarchical_contribution(request: ContributionRequest) -> Tuple[Dict, Dict]:
    """
    Orchestrates the full multi-level, hierarchical position contribution calculation.
    Returns a tuple: (results_dict, lineage_data_dict)
    """
    instruments_df, portfolio_results_df = _prepare_hierarchical_data(request)

    daily_contributions_df = _calculate_daily_instrument_contributions(
        instruments_df, portfolio_results_df, request.weighting_scheme, request.smoothing
    )

    # --- Aggregation Logic ---
    # 1. Calculate total contribution and average weight for each instrument
    totals = daily_contributions_df.groupby("position_id").agg(
        contribution=("smoothed_contribution", "sum"),
        weight_avg=("daily_weight", "mean")
    ).reset_index()

    # --- Residual Allocation ---
    port_ror_series = portfolio_results_df[PortfolioColumns.DAILY_ROR.value] / 100
    total_portfolio_return = (1 + port_ror_series).prod() - 1
    sum_of_contributions = totals["contribution"].sum()
    residual = total_portfolio_return - sum_of_contributions
    total_avg_weight = totals["weight_avg"].sum()

    if total_avg_weight != 0 and request.smoothing.method == "CARINO":
        totals["weight_proportion"] = totals["weight_avg"] / total_avg_weight
        totals["contribution"] += residual * totals["weight_proportion"]

    # Merge metadata back in for grouping, ensuring columns are unique
    temp_meta_cols = ["position_id"] + request.hierarchy
    metadata_cols = list(dict.fromkeys(temp_meta_cols))
    unique_meta = daily_contributions_df[metadata_cols].drop_duplicates()
    aggregated_df = pd.merge(totals, unique_meta, on="position_id")

    # 2. Perform bottom-up aggregation for each level
    response_levels = []
    for i, level_name in enumerate(request.hierarchy):
        level_keys = request.hierarchy[:i+1]
        level_agg = aggregated_df.groupby(level_keys).agg(
            contribution=("contribution", "sum"),
            weight_avg=("weight_avg", "sum")
        ).reset_index()

        rows = []
        for _, row in level_agg.iterrows():
            key_dict = {key: row[key] for key in level_keys}
            rows.append({
                "key": key_dict,
                "contribution": row["contribution"] * 100,
                "weight_avg": row["weight_avg"] * 100,
            })

        response_levels.append({
            "level": i + 1,
            "name": level_name,
            "parent": request.hierarchy[i-1] if i > 0 else None,
            "rows": rows
        })

    # 3. Populate final summary
    portfolio_contribution = aggregated_df["contribution"].sum()
    summary = {
        "portfolio_contribution": portfolio_contribution * 100,
        "coverage_mv_pct": 100.0,  # Placeholder
        "weighting_scheme": request.weighting_scheme.value,
    }
    
    results = {"summary": summary, "levels": response_levels}
    lineage_data = {
        "portfolio_twr.csv": portfolio_results_df,
        "daily_contributions.csv": daily_contributions_df
    }

    return results, lineage_data


def _calculate_single_period_weights(
    portfolio_row: pd.Series,
    positions_df_map: Dict[str, pd.DataFrame],
    day_index: int
) -> Dict[str, float]:
    """Calculates the weight of each position for a single time period (a day)."""
    weights = {}
    portfolio_avg_capital = portfolio_row[PortfolioColumns.BEGIN_MV.value] + portfolio_row[PortfolioColumns.BOD_CF.value]

    if portfolio_avg_capital == 0:
        return {pos_id: 0.0 for pos_id in positions_df_map}

    for pos_id, pos_df in positions_df_map.items():
        pos_row = pos_df.iloc[day_index]
        pos_avg_capital = pos_row[PortfolioColumns.BEGIN_MV.value] + pos_row[PortfolioColumns.BOD_CF.value]
        weights[pos_id] = pos_avg_capital / portfolio_avg_capital

    return weights


def _calculate_carino_factors(ror_series: pd.Series) -> pd.Series:
    """Calculates the Carino smoothing factor k for a series of returns."""
    # Convert index to datetime if it's not already, for potential merges
    if not isinstance(ror_series.index, pd.DatetimeIndex):
        ror_series.index = pd.to_datetime(ror_series.index)

    return pd.Series(
        np.where(
            ror_series == 0,
            1.0,
            np.log(1 + ror_series) / ror_series
        ),
        index=ror_series.index
    )


def calculate_position_contribution(
    portfolio_results: pd.DataFrame,
    position_results_map: Dict[str, pd.DataFrame],
    smoothing: Smoothing,
    emit: Emit,
) -> Dict[str, Dict]:
    """
    Orchestrates the original single-level position contribution calculation.
    """
    portfolio_date_index = pd.to_datetime(portfolio_results[PortfolioColumns.PERF_DATE.value])
    aligned_position_results = {}
    for pos_id, pos_df in position_results_map.items():
        pos_df_indexed = pos_df.set_index(pd.to_datetime(pos_df[PortfolioColumns.PERF_DATE.value]))
        aligned_df = pos_df_indexed.reindex(portfolio_date_index, fill_value=0.0)
        aligned_df[PortfolioColumns.PERF_DATE.value] = aligned_df.index.date
        aligned_position_results[pos_id] = aligned_df.reset_index(drop=True)

    position_results_map = aligned_position_results

    port_daily_ror = portfolio_results.set_index(pd.to_datetime(portfolio_results[PortfolioColumns.PERF_DATE.value]))[PortfolioColumns.DAILY_ROR.value] / 100
    port_total_ror = (1 + port_daily_ror).prod() - 1

    k_daily = _calculate_carino_factors(port_daily_ror) if smoothing.method == "CARINO" else pd.Series(1.0, index=port_daily_ror.index)
    K_total = (np.log(1 + port_total_ror) / port_total_ror if port_total_ror != 0 else 1.0) if smoothing.method == "CARINO" else 1.0

    daily_contributions = []
    daily_weights_list = []
    position_ids = list(position_results_map.keys())

    for i, port_row in portfolio_results.iterrows():
        daily_weights = _calculate_single_period_weights(port_row, position_results_map, i)
        daily_weights_list.append(daily_weights)

        row_contribs = {"date": port_row[PortfolioColumns.PERF_DATE.value]}
        for pos_id in position_ids:
            pos_ror_t = position_results_map[pos_id].iloc[i][PortfolioColumns.DAILY_ROR.value] / 100
            weight_t = daily_weights.get(pos_id, 0.0)

            c_p_t = weight_t * pos_ror_t
            smoothed_c = c_p_t

            if smoothing.method == "CARINO":
                ror_port_t = port_daily_ror.iloc[i]
                k_t = k_daily.iloc[i]
                adjustment = weight_t * (ror_port_t * ((K_total / k_t) - 1)) if k_t != 0 else 0.0
                smoothed_c += adjustment

            if port_row[PortfolioColumns.NIP.value] == 1 or port_row[PortfolioColumns.PERF_RESET.value] == 1:
                smoothed_c = 0.0

            row_contribs[pos_id] = smoothed_c
        daily_contributions.append(row_contribs)

    contrib_df = pd.DataFrame(daily_contributions)
    daily_weights_df = pd.DataFrame(daily_weights_list)
    total_smoothed_contributions = contrib_df[position_ids].sum()

    is_reset = portfolio_results[PortfolioColumns.PERF_RESET.value] == 1
    last_reset_idx = -1
    if is_reset.any():
        last_reset_idx = portfolio_results.index[is_reset].max()

    valid_days_mask = (portfolio_results[PortfolioColumns.NIP.value] != 1) & (portfolio_results.index > last_reset_idx)
    adjusted_day_count = valid_days_mask.sum()

    if adjusted_day_count > 0:
        total_valid_weights = daily_weights_df[valid_days_mask].sum()
        average_weights = total_valid_weights / adjusted_day_count
    else:
        average_weights = pd.Series(0.0, index=position_ids)

    final_results = {}
    for pos_id in position_ids:
        pos_total_return = (1 + (position_results_map[pos_id][PortfolioColumns.DAILY_ROR.value] / 100)).prod() - 1

        final_results[pos_id] = {
            "total_contribution": total_smoothed_contributions[pos_id] * 100,
            "average_weight": average_weights.get(pos_id, 0.0) * 100,
            "total_return": pos_total_return * 100
        }

    sum_of_contributions = sum(data["total_contribution"] / 100 for data in final_results.values())
    residual = port_total_ror - sum_of_contributions

    sum_of_weights = sum(data["average_weight"] for data in final_results.values())
    if sum_of_weights != 0 and smoothing.method == "CARINO":
        for pos_id in position_ids:
            weight_proportion = final_results[pos_id]["average_weight"] / sum_of_weights
            final_results[pos_id]["total_contribution"] += residual * weight_proportion * 100

    if emit.timeseries:
        final_results["timeseries"] = contrib_df[["date"] + position_ids].to_dict(orient="records")

    return final_results