# engine/contribution.py
from typing import Dict
import numpy as np
import pandas as pd

from engine.schema import PortfolioColumns


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
    position_results_map: Dict[str, pd.DataFrame]
) -> Dict[str, Dict]:
    """
    Orchestrates the full position contribution calculation using Carino smoothing.
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

    k_daily = _calculate_carino_factors(port_daily_ror)
    K_total = np.log(1 + port_total_ror) / port_total_ror if port_total_ror != 0 else 1.0

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
            
            ror_port_t = port_daily_ror.iloc[i]
            k_t = k_daily.iloc[i]
            
            adjustment = weight_t * (ror_port_t * ((K_total / k_t) - 1)) if k_t != 0 else 0.0
            smoothed_c = c_p_t + adjustment
            
            if port_row[PortfolioColumns.NIP] == 1 or port_row[PortfolioColumns.PERF_RESET] == 1:
                smoothed_c = 0.0
            
            row_contribs[pos_id] = smoothed_c
        daily_contributions.append(row_contribs)

    contrib_df = pd.DataFrame(daily_contributions)
    daily_weights_df = pd.DataFrame(daily_weights_list)
    total_smoothed_contributions = contrib_df[position_ids].sum()

    # FIX: Implement RFC-004 Adjusted Average Weight Calculation
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
    # --- End FIX ---

    final_results = {}
    for pos_id in position_ids:
        pos_total_return = (1 + (position_results_map[pos_id][PortfolioColumns.DAILY_ROR] / 100)).prod() - 1
        
        final_results[pos_id] = {
            "total_contribution": total_smoothed_contributions[pos_id],
            "average_weight": average_weights.get(pos_id, 0.0),
            "total_return": pos_total_return
        }

    sum_of_contributions = sum(data["total_contribution"] for data in final_results.values())
    residual = port_total_ror - sum_of_contributions
    
    sum_of_weights = sum(data["average_weight"] for data in final_results.values())
    if sum_of_weights != 0:
        for pos_id in position_ids:
            weight_proportion = final_results[pos_id]["average_weight"] / sum_of_weights
            final_results[pos_id]["total_contribution"] += residual * weight_proportion

    return final_results