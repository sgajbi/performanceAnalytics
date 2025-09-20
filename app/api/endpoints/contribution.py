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

    # --- 1. Handle backward compatibility and resolve periods ---
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
    
    # --- 2. Perform Calculations for each period ---
    # TODO: Refactor contribution engine for a "calculate once, slice many" pattern.
    results_by_period = {}
    diagnostics_data = {}  # Store diagnostics from the first run

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
            if period_request.hierarchy:
                results, _ = calculate_hierarchical_contribution(period_request)
                period_result = SinglePeriodContributionResult(summary=results.get("summary"), levels=results.get("levels"))
            else:
                twr_config = EngineConfig(
                    performance_start_date=inception_date,
                    report_start_date=period.start_date,
                    report_end_date=period.end_date,
                    metric_basis=period_request.portfolio_data.metric_basis,
                    period_type=period_request.period_type,
                    currency_mode=period_request.currency_mode,
                    report_ccy=period_request.report_ccy,
                    fx=period_request.fx,
                    hedging=period_request.hedging,
                )
                portfolio_df = create_engine_dataframe(
                    [item.model_dump(by_alias=True) for item in period_request.portfolio_data.daily_data]
                )
                portfolio_results, diags = run_calculations(portfolio_df, twr_config)
                if i == 0:
                    diagnostics_data = diags

                position_results_map = {}
                for position in period_request.positions_data:
                    position_df = create_engine_dataframe(
                        [item.model_dump(by_alias=True) for item in position.daily_data]
                    )
                    # This TWR config should be consistent for all positions
                    pos_twr_config = twr_config
                    if period_request.currency_mode == "BOTH" and position.meta.get("currency") != period_request.report_ccy:
                        pass
                    else:
                        pos_twr_config = twr_config.model_copy(update={"currency_mode": "BASE_ONLY"})

                    position_results, _ = run_calculations(position_df, pos_twr_config)
                    position_results_map[position.position_id] = position_results

                contribution_results = calculate_position_contribution(
                    portfolio_results, position_results_map, period_request.smoothing, period_request.emit, twr_config
                )
                raw_timeseries = contribution_results.pop("timeseries", None)
                total_portfolio_return = ((1 + portfolio_results[PortfolioColumns.DAILY_ROR] / 100).prod() - 1) * 100
                position_contributions = [
                    PositionContribution(**data, position_id=pos_id) for pos_id, data in contribution_results.items()
                ]
                total_contribution_sum = sum(pc.total_contribution for pc in position_contributions)

                period_result = SinglePeriodContributionResult(
                    total_portfolio_return=total_portfolio_return,
                    total_contribution=total_contribution_sum,
                    position_contributions=position_contributions,
                )
            results_by_period[period.name] = period_result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during contribution calculation for period '{period.name}': {str(e)}",
            )

    # --- 3. Assemble Final Response ---
    meta = Meta(
        calculation_id=request.calculation_id,
        engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode,
        calendar=request.calendar,
        annualization=request.annualization,
        periods={"requested": [p.value for p in periods_to_resolve], "master_start": str(master_start_date), "master_end": str(master_end_date)},
        input_fingerprint=input_fingerprint,
        calculation_hash=calculation_hash,
        report_ccy=request.report_ccy,
    )
    diagnostics = Diagnostics(
        nip_days=diagnostics_data.get("nip_days", 0),
        reset_days=diagnostics_data.get("reset_days", 0),
        effective_period_start=diagnostics_data.get("effective_period_start", master_start_date),
        notes=diagnostics_data.get("notes", []),
    )
    audit = Audit(counts={"input_positions": len(request.positions_data)})

    # For backward compatibility, if only one period was requested via legacy field, populate the legacy fields.
    if request.period_type and len(resolved_periods) == 1:
        single_result = list(results_by_period.values())[0]
        response_model = ContributionResponse(
            calculation_id=request.calculation_id,
            portfolio_number=request.portfolio_number,
            report_start_date=master_start_date,
            report_end_date=master_end_date,
            **single_result.model_dump(exclude_none=True),
            meta=meta,
            diagnostics=diagnostics,
            audit=audit,
        )
    else:
        response_model = ContributionResponse(
            calculation_id=request.calculation_id,
            portfolio_number=request.portfolio_number,
            results_by_period=results_by_period,
            meta=meta,
            diagnostics=diagnostics,
            audit=audit,
        )

    # Lineage capture can be added here
    return response_model