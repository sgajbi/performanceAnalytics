# app/api/endpoints/contribution.py
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
import pandas as pd
from adapters.api_adapter import create_engine_dataframe
from app.core.config import get_settings
from app.models.contribution_requests import ContributionRequest
from app.models.contribution_responses import (
    ContributionResponse,
    DailyContribution,
    PositionContribution,
    PositionContributionSeries,
    PositionDailyContribution,
    SinglePeriodContributionResult,
)
from core.envelope import Audit, Diagnostics, Meta
from core.periods import resolve_periods
from core.repro import generate_canonical_hash
from app.services.lineage_service import lineage_service
from engine.compute import run_calculations
from engine.contribution import calculate_hierarchical_contribution, calculate_position_contribution
from engine.config import EngineConfig
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

    if request.period_type:
        periods_to_resolve = [request.period_type]
    else:
        periods_to_resolve = request.periods

    as_of_date = request.as_of or request.report_end_date
    inception_date = request.portfolio_data.daily_data[0].perf_date if request.portfolio_data.daily_data else as_of_date
    resolved_periods = resolve_periods(periods_to_resolve, as_of_date, inception_date)

    if not resolved_periods:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid periods could be resolved.")

    master_start_date = min(p.start_date for p in resolved_periods)
    master_end_date = max(p.end_date for p in resolved_periods)

    results_by_period = {}
    diagnostics_data = {} # Stored from the first/widest run
    lineage_details = {}

    for i, period in enumerate(resolved_periods):
        period_request = request.model_copy(
            update={
                "report_start_date": period.start_date,
                "report_end_date": period.end_date,
                "period_type": "EXPLICIT",
                "periods": None,
            }
        )
        
        try:
            # UNIFIED PATH: Treat single-level as a special case of hierarchical
            is_single_level = not period_request.hierarchy
            if is_single_level:
                period_request.hierarchy = ["position_id"]

            results, period_lineage = calculate_hierarchical_contribution(period_request)
            
            if i == 0:
                lineage_details = period_lineage
                # TODO: Plumb diagnostics out of the hierarchical engine
                diagnostics_data = {"nip_days": 0, "reset_days": 0, "effective_period_start": period.start_date, "notes": []}

            if is_single_level:
                # Unpack the hierarchical result into the single-level format
                total_return = results["summary"]["portfolio_contribution"]
                position_level = results["levels"][0]
                pos_contribs = [
                    PositionContribution(
                        position_id=row["key"]["position_id"],
                        total_contribution=row["contribution"],
                        average_weight=row["weight_avg"],
                        total_return=0, # This requires another engine run; defer for now.
                        local_contribution=row.get("local_contribution"),
                        fx_contribution=row.get("fx_contribution")
                    ) for row in position_level["rows"]
                ]
                period_result = SinglePeriodContributionResult(
                    total_portfolio_return=total_return,
                    total_contribution=total_return,
                    position_contributions=pos_contribs
                )
            else:
                period_result = SinglePeriodContributionResult(summary=results.get("summary"), levels=results.get("levels"))

            results_by_period[period.name] = period_result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during contribution calculation for period '{period.name}': {str(e)}",
            )

    meta = Meta(
        calculation_id=request.calculation_id, engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode, calendar=request.calendar,
        annualization=request.annualization,
        periods={"requested": [p.value for p in periods_to_resolve], "master_start": str(master_start_date), "master_end": str(master_end_date)},
        input_fingerprint=input_fingerprint, calculation_hash=calculation_hash, report_ccy=request.report_ccy,
    )
    diagnostics = Diagnostics(
        nip_days=diagnostics_data.get("nip_days", 0),
        reset_days=diagnostics_data.get("reset_days", 0),
        effective_period_start=diagnostics_data.get("effective_period_start", master_start_date),
        notes=diagnostics_data.get("notes", []),
    )
    audit = Audit(counts={"input_positions": len(request.positions_data)})

    if request.period_type and len(resolved_periods) == 1:
        single_result = list(results_by_period.values())[0]
        response_model = ContributionResponse(
            calculation_id=request.calculation_id, portfolio_number=request.portfolio_number,
            report_start_date=master_start_date, report_end_date=master_end_date,
            **single_result.model_dump(exclude_none=True),
            meta=meta, diagnostics=diagnostics, audit=audit,
        )
    else:
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
        calculation_details=lineage_details,
    )

    return response_model