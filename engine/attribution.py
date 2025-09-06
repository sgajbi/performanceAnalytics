# engine/attribution.py
from typing import List
import pandas as pd

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
from common.enums import AttributionMode


def _prepare_panel_from_groups(
    groups: List[PortfolioGroup | BenchmarkGroup], group_by: List[str]
) -> pd.DataFrame:
    """Helper to convert list of group data into a tidy DataFrame panel."""
    all_obs = []
    if not groups:
        return pd.DataFrame()

    for group in groups:
        # For single-level, the tuple will have one element
        group_key_tuple = tuple(group.key.get(k) for k in group_by)
        for obs in group.observations:
            record = {
                'date': pd.to_datetime(obs['date']),
                'return': obs.get('return', 0.0),
                'weight_bop': obs.get('weight_bop', 0.0),
                'group': group_key_tuple,
            }
            all_obs.append(record)

    if not all_obs:
        return pd.DataFrame()

    df = pd.DataFrame(all_obs)
    df = df.set_index(['date', 'group'])
    return df


def _align_and_prepare_data(request: AttributionRequest) -> pd.DataFrame:
    """
    Pre-processes and aligns portfolio and benchmark group data for attribution.
    NOTE: Phase 2 implementation for 'by_group' mode and single level.
    """
    if request.mode != AttributionMode.BY_GROUP:
        return pd.DataFrame()

    # 1. Convert input data to tidy panels
    portfolio_panel = _prepare_panel_from_groups(
        request.portfolio_groups_data, request.group_by
    )
    benchmark_panel = _prepare_panel_from_groups(
        request.benchmark_groups_data, request.group_by
    )

    if portfolio_panel.empty or benchmark_panel.empty:
        return pd.DataFrame()

    # 2. Resample to the desired frequency
    freq_map = {'daily': 'D', 'monthly': 'M', 'quarterly': 'Q', 'yearly': 'Y'}
    freq_code = freq_map.get(request.frequency.value, 'M')

    resampler_p = portfolio_panel.unstack('group').resample(freq_code)
    resampler_b = benchmark_panel.unstack('group').resample(freq_code)

    portfolio_returns = resampler_p['return'].apply(
        lambda x: (1 + x).prod() - 1 if not x.empty else None
    )
    benchmark_returns = resampler_b['return'].apply(
        lambda x: (1 + x).prod() - 1 if not x.empty else None
    )

    portfolio_weights = resampler_p['weight_bop'].first()
    benchmark_weights = resampler_b['weight_bop'].first()

    # 3. Combine into final aligned DataFrame
    df_p = pd.concat([portfolio_returns.stack(), portfolio_weights.stack()], axis=1).rename(
        columns={0: 'r_p', 1: 'w_p'}
    )
    df_b = pd.concat([benchmark_returns.stack(), benchmark_weights.stack()], axis=1).rename(
        columns={0: 'r_b', 1: 'w_b'}
    )

    df_p.index.names = ['date', 'group']
    df_b.index.names = ['date', 'group']

    aligned_df = pd.merge(
        df_p, df_b, left_index=True, right_index=True, how='outer'
    ).fillna(0.0)

    # 4. Calculate total benchmark return for each period
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


def run_attribution_calculations(request: AttributionRequest) -> AttributionResponse:
    """
    Orchestrates the full multi-level performance attribution calculation.
    NOTE: This is a placeholder implementation.
    """
    dummy_level = AttributionLevelResult(
        dimension=request.group_by[0],
        groups=[],
        totals=AttributionLevelTotals(
            allocation=0.0, selection=0.0, interaction=0.0, total_effect=0.0
        ),
    )
    return AttributionResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        model=request.model,
        linking=request.linking,
        levels=[dummy_level],
        reconciliation=Reconciliation(
            total_active_return=0.0, sum_of_effects=0.0, residual=0.0
        ),
    )