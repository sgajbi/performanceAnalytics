# engine/attribution.py
import pandas as pd
from app.models.attribution_requests import AttributionRequest, AttributionModel
from app.models.attribution_responses import (
    AttributionGroupResult,
    AttributionLevelResult,
    AttributionLevelTotals,
    AttributionResponse,
    Reconciliation,
)


def _calculate_single_period_effects(df: pd.DataFrame, model: AttributionModel) -> pd.DataFrame:
    """
    Calculates single-period attribution effects (A, S, I) for an aligned DataFrame.

    Args:
        df: DataFrame with columns ['w_p', 'r_p', 'w_b', 'r_b'] and indexed by group.
            It must also contain the total benchmark return 'r_b_total' for each period.
    Returns:
        DataFrame with added columns for 'allocation', 'selection', 'interaction'.
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
    NOTE: This is a placeholder implementation for Phase 1.
    """
    # This placeholder returns a valid but dummy response to satisfy the API contract.
    # The actual implementation will be built in subsequent, test-driven phases.
    dummy_level = AttributionLevelResult(
        dimension=request.group_by[0],
        groups=[],
        totals=AttributionLevelTotals(
            allocation=0.0, selection=0.0, interaction=0.0, total_effect=0.0
        ),
    )

    dummy_response = AttributionResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        model=request.model,
        linking=request.linking,
        levels=[dummy_level],
        reconciliation=Reconciliation(
            total_active_return=0.0, sum_of_effects=0.0, residual=0.0
        ),
    )
    return dummy_response