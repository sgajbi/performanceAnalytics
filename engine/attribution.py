# engine/attribution.py
from typing import List
import pandas as pd
import numpy as np

from app.models.attribution_requests import (
    AttributionRequest,
    AttributionModel,
    PortfolioGroup,
    BenchmarkGroup,
)
from app.models.attribution_responses import (
    AttributionGroupResult,
    AttributionLevelResult,
    AttributionLevelTotals,
    AttributionResponse,
    Reconciliation,
)
from common.enums import AttributionMode, LinkingMethod


def _prepare_panel_from_groups(
    groups: List[PortfolioGroup | BenchmarkGroup], group_by: List[str]
) -> pd.DataFrame:
    """Helper to convert list of group data into a tidy DataFrame panel."""
    all_obs = []
    if not groups:
        return pd.DataFrame()

    for group in groups:
        group_key_tuple = tuple(group.key.get(k) for k in group_by)
        for obs in group.observations:
            record = {
                'date': pd.to_datetime(obs['date']),
                'return': obs.get('return', 0.0),
                'weight_bop': obs.get('weight_bop', 0.0),
            }
            for i, key in enumerate(group_by):
                record[f'group_{i}'] = group_key_tuple[i]
            all_obs.append(record)

    if not all_obs:
        return pd.DataFrame()

    df = pd.DataFrame(all_obs)
    group_cols = [f'group_{i}' for i in range(len(group_by))]
    df = df.set_index(['date'] + group_cols)
    return df


def _align_and_prepare_data(request: AttributionRequest) -> pd.DataFrame:
    """
    Pre-processes and aligns portfolio and benchmark group data for attribution.
    """
    if request.mode != AttributionMode.BY_GROUP:
        return pd.DataFrame()

    group_by = request.group_by
    group_cols = [f'group_{i}' for i in range(len(group_by))]
    portfolio_panel = _prepare_panel_from_groups(request.portfolio_groups_data, group_by)
    benchmark_panel = _prepare_panel_from_groups(request.benchmark_groups_data, group_by)

    if portfolio_panel.empty or benchmark_panel.empty:
        return pd.DataFrame()

    freq_map = {'daily': 'D', 'monthly': 'ME', 'quarterly': 'QE', 'yearly': 'YE'}
    freq_code = freq_map.get(request.frequency.value, 'ME')

    resampler_p = portfolio_panel.unstack(level=group_cols).resample(freq_code)
    resampler_b = benchmark_panel.unstack(level=group_cols).resample(freq_code)

    portfolio_returns = resampler_p['return'].apply(lambda x: (1 + x).prod() - 1 if not x.empty else None)
    benchmark_returns = resampler_b['return'].apply(lambda x: (1 + x).prod() - 1 if not x.empty else None)

    portfolio_weights = resampler_p['weight_bop'].first()
    benchmark_weights = resampler_b['weight_bop'].first()

    df_p = pd.concat([portfolio_returns.stack(group_cols), portfolio_weights.stack(group_cols)], axis=1)
    df_p.columns = ['r_p', 'w_p']
    df_b = pd.concat([benchmark_returns.stack(group_cols), benchmark_weights.stack(group_cols)], axis=1)
    df_b.columns = ['r_b', 'w_b']

    aligned_df = pd.merge(df_p, df_b, left_index=True, right_index=True, how='outer').fillna(0.0)
    aligned_df.index.names = ['date'] + group_cols

    total_benchmark_return = (aligned_df['w_b'] * aligned_df['r_b']).groupby(level='date').sum()
    aligned_df = aligned_df.join(total_benchmark_return.rename('r_b_total'), on='date')

    return aligned_df


def _calculate_single_period_effects(df: pd.DataFrame, model: AttributionModel) -> pd.DataFrame:
    """
    Calculates single-period attribution effects (A, S, I) for an aligned DataFrame.
    """
    if model == AttributionModel.BRINSON_FACHLER:
        df['allocation'] = (df['w_p'] - df['w_b']) * (df['r_b'] - df['r_b_total'])
        df['selection'] = df['w_b'] * (df['r_p'] - df['r_b'])
        df['interaction'] = (df['w_p'] - df['w_b']) * (df['r_p'] - df['r_b'])
    elif model == AttributionModel.BRINSON_HOOD_BEEBOWER:
        df['allocation'] = (df['w_p'] - df['w_b']) * df['r_b']
        df['selection'] = df['w_p'] * (df['r_p'] - df['r_b'])
        df['interaction'] = (df['w_p'] - df['w_b']) * (df['r_p'] - df['r_b'])

    return df


def _link_effects_menchero(effects_df: pd.DataFrame, per_period_b_return: pd.Series) -> pd.DataFrame:
    """Links multi-period attribution effects using the Menchero algorithm."""
    # Calculate the cumulative benchmark return from each period to the end
    reversed_growth = (1 + per_period_b_return).iloc[::-1].cumprod().iloc[::-1]
    # The linking factor for period t is the benchmark's growth from t+1 to N
    linking_factors = reversed_growth / (1 + per_period_b_return)
    linking_factors.name = 'factor'

    effects_with_factors = effects_df.join(linking_factors, on='date')
    
    linked_effects = effects_df[['allocation', 'selection', 'interaction']].copy()
    for col in linked_effects.columns:
        linked_effects[col] *= effects_with_factors['factor']
        
    return linked_effects


def run_attribution_calculations(request: AttributionRequest) -> AttributionResponse:
    """
    Orchestrates the full multi-level performance attribution calculation.
    """
    if request.mode != AttributionMode.BY_GROUP or len(request.group_by) > 1:
        raise NotImplementedError("Only single-level 'by_group' mode is supported.")

    aligned_df = _align_and_prepare_data(request)

    if aligned_df.empty:
        dummy_level = AttributionLevelResult(dimension=request.group_by[0], groups=[], totals=AttributionLevelTotals(allocation=0.0, selection=0.0, interaction=0.0, total_effect=0.0))
        return AttributionResponse(calculation_id=request.calculation_id, portfolio_number=request.portfolio_number, model=request.model, linking=request.linking, levels=[dummy_level], reconciliation=Reconciliation(total_active_return=0.0, sum_of_effects=0.0, residual=0.0))

    group_by_key = 'group_0'
    effects_df = _calculate_single_period_effects(aligned_df, request.model)

    per_period_p_return = (effects_df['w_p'] * effects_df['r_p']).groupby(level='date').sum()
    per_period_b_return = effects_df.groupby(level='date')['r_b_total'].first()

    # The 'linking' parameter from the request is respected, but Menchero is used for geometric linking.
    if request.linking != LinkingMethod.NONE:
        linked_effects = _link_effects_menchero(effects_df, per_period_b_return)
        group_totals = linked_effects.groupby(level=group_by_key).sum()
        active_return = (1 + per_period_p_return).prod() - 1 - ((1 + per_period_b_return).prod() - 1)
    else: # Default to simple arithmetic sum
        group_totals = effects_df.groupby(level=group_by_key)[['allocation', 'selection', 'interaction']].sum()
        active_return = per_period_p_return.sum() - per_period_b_return.sum()

    group_totals['total_effect'] = group_totals.sum(axis=1)
    overall_totals = group_totals.sum()

    group_results = []
    for group_name, row in group_totals.iterrows():
        group_results.append(AttributionGroupResult(key={request.group_by[0]: group_name}, **row.to_dict()))

    level_result = AttributionLevelResult(
        dimension=request.group_by[0],
        groups=sorted(group_results, key=lambda x: x.key[request.group_by[0]]),
        totals=AttributionLevelTotals(**overall_totals.to_dict()),
    )

    return AttributionResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        model=request.model,
        linking=request.linking,
        levels=[level_result],
        reconciliation=Reconciliation(
            total_active_return=active_return,
            sum_of_effects=overall_totals['total_effect'],
            residual=active_return - overall_totals['total_effect']
        ),
    )