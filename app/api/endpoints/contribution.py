# app/api/endpoints/contribution.py
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
import pandas as pd
from adapters.api_adapter import create_engine_dataframe
from app.core.config import get_settings
from app.models.contribution_requests import ContributionRequest
from app.models.contribution_responses import (
    ContributionResponse,
    SinglePeriodContributionResult,
)
from core.envelope import Audit, Diagnostics, Meta
from core.periods import resolve_periods
from core.repro import generate_canonical_hash
from app.services.lineage_service import lineage_service
from engine.contribution import (
    calculate_hierarchical_contribution,
    _prepare_hierarchical_data,
    _calculate_daily_instrument_contributions,
)
from engine.schema import PortfolioColumns

router = APIRouter()
settings = get_settings()


@router.post("/contribution", response_model=ContributionResponse, summary="Calculate Position Contribution")
async def calculate_contribution_endpoint(request: ContributionRequest, background_tasks: BackgroundTasks):
    """
    Calculates the performance contribution for each position within a portfolio
    for one or more requested periods.
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)

    periods_to_resolve = [analysis.period for analysis in request.analyses]
    as_of_date = request.report_end_date
    inception_date = request.portfolio_data.valuation_points[0].perf_date if request.portfolio_data.valuation_points else as_of_date
    resolved_periods = resolve_periods(periods_to_resolve, as_of_date, inception_date)

    if not resolved_periods:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid periods could be resolved.")

    master_start_date = min(p.start_date for p in resolved_periods)
    master_end_date = max(p.end_date for p in resolved_periods)

    try:
        if request.hierarchy:
            results, lineage_details = calculate_hierarchical_contribution(request)
            period_result = SinglePeriodContributionResult(summary=results.get("summary"), levels=results.get("levels"))
            results_by_period = {resolved_periods[0].name: period_result}
            portfolio_results_df = lineage_details.get("portfolio_twr.csv", pd.DataFrame())
        else:
            master_request = request.model_copy(
                update={
                    "report_start_date": master_start_date,
                    "report_end_date": master_end_date,
                }
            )

            instruments_df, portfolio_results_df = _prepare_hierarchical_data(master_request)
            daily_contributions_df = _calculate_daily_instrument_contributions(
                instruments_df, portfolio_results_df, master_request.weighting_scheme, master_request.smoothing
            )
            daily_contributions_df[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(
                daily_contributions_df[PortfolioColumns.PERF_DATE.value]
            ).dt.date

            results_by_period = {}
            for period in resolved_periods:
                period_slice_df = daily_contributions_df[
                    (daily_contributions_df[PortfolioColumns.PERF_DATE.value] >= period.start_date)
                    & (daily_contributions_df[PortfolioColumns.PERF_DATE.value] <= period.end_date)
                ].copy()

                if period_slice_df.empty:
                    continue

                # Remainder of logic for non-hierarchical contribution can be added here if needed

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during contribution calculation: {str(e)}",
        )

    meta = Meta(
        calculation_id=request.calculation_id, engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode, calendar=request.calendar,
        annualization=request.annualization,
        periods={"requested": [p.value for p in periods_to_resolve], "master_start": str(master_start_date), "master_end": str(master_end_date)},
        input_fingerprint=input_fingerprint, calculation_hash=calculation_hash, report_ccy=request.report_ccy,
    )
    diagnostics = Diagnostics(
        nip_days=0, reset_days=0, effective_period_start=master_start_date, notes=[]
    )
    audit = Audit(counts={"input_positions": len(request.positions_data)})

    # The logic to handle single vs. multi-period response structures needs to be updated
    # based on the new 'analyses' model. For now, we simplify to always return by period.
    response_model = ContributionResponse(
        calculation_id=request.calculation_id, portfolio_number=request.portfolio_number,
        results_by_period=results_by_period,
        meta=meta, diagnostics=diagnostics, audit=audit,
    )

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="Contribution",
        request_model=request,
        response_model=response_model,
        calculation_details={
            "portfolio_twr.csv": portfolio_results_df,
            "daily_contributions.csv": pd.DataFrame() # Placeholder
        },
    )

    return response_model