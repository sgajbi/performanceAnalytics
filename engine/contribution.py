# engine/contribution.py
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from app.models.contribution_requests import ContributionRequest, Emit, Smoothing
from engine.schema import PortfolioColumns
from engine.compute import run_calculations
from engine.config import EngineConfig
from adapters.api_adapter import create_engine_dataframe


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

    # 3. Calculate performance for each position and combine with metadata
    all_positions_data = []
    for position in request.positions_data:
        position_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in position.daily_data])
        if position_df.empty:
            continue

        position_results_df, _ = run_calculations(position_df, twr_config)
        position_results_df["position_id"] = position.position_id
        for key, value in position.meta.items():
            position_results_df[key] = value

        all_positions_data.append(position_results_df)

    if not all_positions_data:
        return pd.DataFrame(), portfolio_results_df

    instruments_df = pd.concat(all_positions_data, ignore_index=True)
    return instruments_df, portfolio_results_df


def calculate_hierarchical_contribution(request: ContributionRequest) -> Dict:
    """
    Orchestrates the full multi-level, hierarchical position contribution calculation.
    """
    instruments_df, portfolio_results_df = _prepare_hierarchical_data(request)

    # This is a placeholder implementation. The full logic will be built here
    # in subsequent steps using the prepared DataFrames.
    return {
        "summary": {
            "portfolio_contribution": 0.0,
            "coverage_mv_pct": 100.0,
            "weighting_scheme": request.weighting_scheme.value,
        },
        "levels": [],
    }


def _calculate_single_period_weights(
    portfolio_row: pd.Series,
    positions_df_map: Dict[str, pd.DataFrame],
    day_index: int
) -> Dict[str, float]:
    """Calculates the weight of each position for a single time period (a day)."""
    weights = {}
    portfolio_avg_capital = portfolio_row[PortfolioColumns.BEGIN_MV] + portfolio_row[PortfolioColumns.BOD_CF]

    if portfolio_avg_capital == 0:
        return {pos_id: 0.0 for pos_id in positions_df_map}

    for pos_id, pos_df in positions_df_map.items():
        pos_row = pos_df.iloc[day_index]
        pos_avg_capital = pos_row[PortfolioColumns.BEGIN_MV] + pos_row[PortfolioColumns.BOD_CF]
        weights[pos_id] = pos_avg_capital / portfolio_avg_capital

    return weights


def _calculate_carino_factors(ror_series: pd.Series) -> pd.Series:
    """Calculates the Carino smoothing factor k for a series of returns."""
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
    portfolio_date_index = pd.to_datetime(portfolio_results[PortfolioColumns.PERF_DATE])
    aligned_position_results = {}
    for pos_id, pos_df in position_results_map.items():
        pos_df_indexed = pos_df.set_index(pd.to_datetime(pos_df[PortfolioColumns.PERF_DATE]))
        aligned_df = pos_df_indexed.reindex(portfolio_date_index, fill_value=0.0)
        aligned_df[PortfolioColumns.PERF_DATE] = aligned_df.index.date
        aligned_position_results[pos_id] = aligned_df.reset_index(drop=True)

    position_results_map = aligned_position_results

    port_daily_ror = portfolio_results[PortfolioColumns.DAILY_ROR] / 100
    port_total_ror = (1 + port_daily_ror).prod() - 1

    k_daily = _calculate_carino_factors(port_daily_ror) if smoothing.method == "CARINO" else pd.Series(1.0, index=port_daily_ror.index)
    K_total = (np.log(1 + port_total_ror) / port_total_ror if port_total_ror != 0 else 1.0) if smoothing.method == "CARINO" else 1.0

    daily_contributions = []
    daily_weights_list = []
    position_ids = list(position_results_map.keys())

    for i, port_row in portfolio_results.iterrows():
        daily_weights = _calculate_single_period_weights(port_row, position_results_map, i)
        daily_weights_list.append(daily_weights)

        row_contribs = {"date": port_row[PortfolioColumns.PERF_DATE]}
        for pos_id in position_ids:
            pos_ror_t = position_results_map[pos_id].iloc[i][PortfolioColumns.DAILY_ROR] / 100
            weight_t = daily_weights.get(pos_id, 0.0)

            c_p_t = weight_t * pos_ror_t
            smoothed_c = c_p_t

            if smoothing.method == "CARINO":
                ror_port_t = port_daily_ror.iloc[i]
                k_t = k_daily.iloc[i]
                adjustment = weight_t * (ror_port_t * ((K_total / k_t) - 1)) if k_t != 0 else 0.0
                smoothed_c += adjustment

            if port_row[PortfolioColumns.NIP] == 1 or port_row[PortfolioColumns.PERF_RESET] == 1:
                smoothed_c = 0.0

            row_contribs[pos_id] = smoothed_c
        daily_contributions.append(row_contribs)

    contrib_df = pd.DataFrame(daily_contributions)
    daily_weights_df = pd.DataFrame(daily_weights_list)
    total_smoothed_contributions = contrib_df[position_ids].sum()

    is_reset = portfolio_results[PortfolioColumns.PERF_RESET] == 1
    last_reset_idx = -1
    if is_reset.any():
        last_reset_idx = portfolio_results.index[is_reset].max()

    valid_days_mask = (portfolio_results[PortfolioColumns.NIP] != 1) & (portfolio_results.index > last_reset_idx)
    adjusted_day_count = valid_days_mask.sum()

    if adjusted_day_count > 0:
        total_valid_weights = daily_weights_df[valid_days_mask].sum()
        average_weights = total_valid_weights / adjusted_day_count
    else:
        average_weights = pd.Series(0.0, index=position_ids)

    final_results = {}
    for pos_id in position_ids:
        pos_total_return = (1 + (position_results_map[pos_id][PortfolioColumns.DAILY_ROR] / 100)).prod() - 1

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