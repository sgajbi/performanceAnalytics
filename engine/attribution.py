# engine/attribution.py
from typing import List
import pandas as pd
import numpy as np

from app.models.attribution_requests import (
    AttributionRequest,
    AttributionModel,
    PortfolioGroup,
    BenchmarkGroup,
    InstrumentData,
)
from app.models.attribution_responses import (
    AttributionGroupResult,
    AttributionLevelResult,
    AttributionLevelTotals,
    AttributionResponse,
    Reconciliation,
)
from common.enums import AttributionMode, LinkingMethod, PeriodType
from engine.config import EngineConfig
from engine.compute import run_calculations
from engine.schema import PortfolioColumns
from adapters.api_adapter import create_engine_dataframe


def _prepare_data_from_instruments(request: AttributionRequest) -> List[PortfolioGroup]:
    """
    Runs TWR engine on instrument data and aggregates returns and weights
    up to the requested group levels.
    """
    if not request.portfolio_data or not request.instruments_data:
        raise ValueError("'portfolio_data' and 'instruments_data' are required for 'by_instrument' mode.")

    twr_config = EngineConfig(
        performance_start_date=request.portfolio_data.report_start_date,
        report_start_date=request.portfolio_data.report_start_date,
        report_end_date=request.portfolio_data.report_end_date,
        metric_basis=request.portfolio_data.metric_basis,
        period_type=PeriodType.ITD,
    )

    portfolio_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in request.portfolio_data.daily_data])
    portfolio_df[PortfolioColumns.PERF_DATE] = pd.to_datetime(portfolio_df[PortfolioColumns.PERF_DATE])
    portfolio_df = portfolio_df.set_index(PortfolioColumns.PERF_DATE)
    portfolio_bop_mv = portfolio_df[PortfolioColumns.BEGIN_MV] + portfolio_df[PortfolioColumns.BOD_CF]

    all_instruments = []
    for inst in request.instruments_data:
        inst_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in inst.daily_data])
        if inst_df.empty: continue

        inst_results, _ = run_calculations(inst_df.copy(), twr_config)
        inst_results[PortfolioColumns.PERF_DATE] = pd.to_datetime(inst_results[PortfolioColumns.PERF_DATE])
        inst_results = inst_results.set_index(PortfolioColumns.PERF_DATE)

        inst_bop_mv = inst_results[PortfolioColumns.BEGIN_MV] + inst_results[PortfolioColumns.BOD_CF]
        inst_results['weight_bop'] = inst_bop_mv / portfolio_bop_mv

        for key, value in inst.meta.items():
            inst_results[key] = value
        all_instruments.append(inst_results.reset_index())

    if not all_instruments: return []

    full_df = pd.concat(all_instruments)
    group_cols = request.group_by

    full_df['weighted_ror'] = (full_df[PortfolioColumns.DAILY_ROR] / 100) * full_df['weight_bop']

    grouped = full_df.groupby([PortfolioColumns.PERF_DATE] + group_cols)
    group_weights = grouped['weight_bop'].sum()
    group_weighted_ror = grouped['weighted_ror'].sum()

    with np.errstate(divide='ignore', invalid='ignore'):
        group_returns = (group_weighted_ror / group_weights).fillna(0.0)

    aggregated_panel = pd.DataFrame({'return': group_returns, 'weight_bop': group_weights}).reset_index()

    output_groups = []
    for keys, group_df in aggregated_panel.groupby(group_cols):
        key_dict = {group_cols[i]: key_val for i, key_val in enumerate(keys if isinstance(keys, tuple) else [keys])}
        output_groups.append(
            PortfolioGroup(
                key=key_dict,
                observations=group_df[[PortfolioColumns.PERF_DATE, 'return', 'weight_bop']].rename(columns={PortfolioColumns.PERF_DATE: 'date'}).to_dict(orient='records')
            )
        )
    return output_groups


def _prepare_panel_from_groups(
    groups: List[PortfolioGroup | BenchmarkGroup], group_by: List[str]
) -> pd.DataFrame:
    """Helper to convert list of group data into a tidy DataFrame panel."""
    all_obs = []
    if not groups: return pd.DataFrame()

    for group in groups:
        group_key_tuple = tuple(group.key.get(k) for k in group_by)
        for obs in group.observations:
            record = {'date': pd.to_datetime(obs['date']), 'return': obs.get('return', 0.0), 'weight_bop': obs.get('weight_bop', 0.0)}
            for i, key in enumerate(group_by): record[key] = group_key_tuple[i]
            all_obs.append(record)

    if not all_obs: return pd.DataFrame()
    df = pd.DataFrame(all_obs)
    return df.set_index(['date'] + group_by)


def _align_and_prepare_data(request: AttributionRequest, portfolio_groups_data: List[PortfolioGroup]) -> pd.DataFrame:
    """Pre-processes and aligns portfolio and benchmark group data for attribution."""
    group_by = request.group_by
    portfolio_panel = _prepare_panel_from_groups(portfolio_groups_data, group_by)
    benchmark_panel = _prepare_panel_from_groups(request.benchmark_groups_data, group_by)

    if portfolio_panel.empty or benchmark_panel.empty: return pd.DataFrame()
    freq_map = {'daily': 'D', 'monthly': 'ME', 'quarterly': 'QE', 'yearly': 'YE'}
    freq_code = freq_map.get(request.frequency.value, 'ME')

    resampler_p = portfolio_panel.unstack(level=group_by).resample(freq_code)
    resampler_b = benchmark_panel.unstack(level=group_by).resample(freq_code)
    portfolio_returns = resampler_p['return'].apply(lambda x: (1 + x).prod() - 1 if not x.empty else None)
    benchmark_returns = resampler_b['return'].apply(lambda x: (1 + x).prod() - 1 if not x.empty else None)
    portfolio_weights = resampler_p['weight_bop'].first()
    benchmark_weights = resampler_b['weight_bop'].first()

    df_p = pd.concat([portfolio_returns.stack(group_by, future_stack=True), portfolio_weights.stack(group_by, future_stack=True)], axis=1); df_p.columns = ['r_p', 'w_p']
    df_b = pd.concat([benchmark_returns.stack(group_by, future_stack=True), benchmark_weights.stack(group_by, future_stack=True)], axis=1); df_b.columns = ['r_b', 'w_b']
    aligned_df = pd.merge(df_p, df_b, left_index=True, right_index=True, how='outer').fillna(0.0)
    aligned_df.index.names = ['date'] + group_by
    total_benchmark_return = (aligned_df['w_b'] * aligned_df['r_b']).groupby(level='date').sum()
    return aligned_df.join(total_benchmark_return.rename('r_b_total'), on='date')


def _calculate_single_period_effects(df: pd.DataFrame, model: AttributionModel) -> pd.DataFrame:
    """Calculates single-period attribution effects (A, S, I) for an aligned DataFrame."""
    if model == AttributionModel.BRINSON_FACHLER:
        df['allocation'] = (df['w_p'] - df['w_b']) * (df['r_b'] - df['r_b_total'])
        df['selection'] = df['w_b'] * (df['r_p'] - df['r_b'])
        df['interaction'] = (df['w_p'] - df['w_b']) * (df['r_p'] - df['r_b'])
    elif model == AttributionModel.BRINSON_HOOD_BEEBOWER:
        # BHB model defines Allocation differently and has no Interaction effect by standard definition,
        # but for consistency we calculate it. Selection is often defined differently as well.
        # This implementation uses a common variant.
        df['allocation'] = (df['w_p'] - df['w_b']) * df['r_b']
        df['selection'] = df['w_p'] * (df['r_p'] - df['r_b'])
        df['interaction'] = (df['w_p'] - df['w_b']) * (df['r_p'] - df['r_b'])
    return df


def _link_effects_top_down(effects_df: pd.DataFrame, geometric_total_ar: float, arithmetic_total_ar: float) -> pd.DataFrame:
    """Links multi-period effects by scaling the arithmetic sum to match the geometric total."""
    if arithmetic_total_ar == 0:
        return effects_df
    
    scaling_factor = geometric_total_ar / arithmetic_total_ar
    
    linked_effects = effects_df.copy()
    for col in ['allocation', 'selection', 'interaction']:
        linked_effects[col] *= scaling_factor
        
    return linked_effects


def run_attribution_calculations(request: AttributionRequest) -> AttributionResponse:
    """Orchestrates the full multi-level performance attribution calculation."""
    if request.mode == AttributionMode.BY_INSTRUMENT:
        portfolio_groups_data = _prepare_data_from_instruments(request)
    elif request.mode == AttributionMode.BY_GROUP:
        portfolio_groups_data = request.portfolio_groups_data
    else:
        raise ValueError("Invalid attribution mode specified.")

    aligned_df = _align_and_prepare_data(request, portfolio_groups_data)
    if aligned_df.empty:
        dummy_level = AttributionLevelResult(dimension=request.group_by[0], groups=[], totals=AttributionLevelTotals(allocation=0.0, selection=0.0, interaction=0.0, total_effect=0.0))
        return AttributionResponse(calculation_id=request.calculation_id, portfolio_number=request.portfolio_number, model=request.model, linking=request.linking, levels=[dummy_level], reconciliation=Reconciliation(total_active_return=0.0, sum_of_effects=0.0, residual=0.0))

    effects_df = _calculate_single_period_effects(aligned_df.reset_index(), request.model)
    per_period_p_return = (effects_df.set_index('date')['w_p'] * effects_df.set_index('date')['r_p']).groupby(level='date').sum()
    per_period_b_return = effects_df.groupby('date')['r_b_total'].first()
    per_period_active_return = per_period_p_return - per_period_b_return

    if request.linking != LinkingMethod.NONE:
        geometric_active_return = (1 + per_period_p_return).prod() - 1 - ((1 + per_period_b_return).prod() - 1)
        arithmetic_active_return = per_period_active_return.sum()
        scaled_effects = _link_effects_top_down(effects_df, geometric_active_return, arithmetic_active_return)
        granular_totals = scaled_effects.groupby(request.group_by)[['allocation', 'selection', 'interaction']].sum()
        active_return = geometric_active_return
    else:
        granular_totals = effects_df.groupby(request.group_by)[['allocation', 'selection', 'interaction']].sum()
        active_return = per_period_active_return.sum()

    levels = []
    granular_totals_df = granular_totals.reset_index()
    
    for i in range(len(request.group_by), 0, -1):
        level_group_by = request.group_by[:i]
        level_totals = granular_totals_df.groupby(level_group_by).sum(numeric_only=True)
        level_totals['total_effect'] = level_totals.sum(axis=1)

        group_results = []
        for group_key, row in level_totals.iterrows():
            key_dict = {}
            if isinstance(group_key, tuple):
                for j, key_name in enumerate(level_group_by):
                    key_dict[key_name] = group_key[j]
            else:
                key_dict[level_group_by[0]] = group_key
            group_results.append(AttributionGroupResult(key=key_dict, **(row * 100).to_dict()))

        overall_level_totals = level_totals.sum()
        levels.append(AttributionLevelResult(
            dimension=" -> ".join(level_group_by),
            groups=sorted(group_results, key=lambda x: str(x.key)),
            totals=AttributionLevelTotals(**(overall_level_totals * 100).to_dict()),
        ))
    
    levels.reverse() # Present from top-level to granular
    final_totals = levels[0].totals

    return AttributionResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        model=request.model,
        linking=request.linking,
        levels=levels,
        reconciliation=Reconciliation(
            total_active_return=active_return * 100,
            sum_of_effects=final_totals.total_effect,
            residual=(active_return * 100) - final_totals.total_effect
        ),
    )