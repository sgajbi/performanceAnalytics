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
)
from core.envelope import Audit, Diagnostics, Meta
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
    Calculates the performance contribution for each position within a portfolio.
    - If a `hierarchy` is provided, it performs a multi-level breakdown.
    - Otherwise, it calculates contribution at the individual position level.
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)

    # 1. Create shared TWR config and diagnostics object from the request
    try:
        perf_start_date = request.portfolio_data.daily_data[0].perf_date
        twr_config = EngineConfig(
            performance_start_date=perf_start_date,
            report_start_date=request.portfolio_data.report_start_date,
            report_end_date=request.portfolio_data.report_end_date,
            metric_basis=request.portfolio_data.metric_basis,
            period_type=request.portfolio_data.period_type,
            precision_mode=request.precision_mode,
            rounding_precision=request.rounding_precision,
            data_policy=request.data_policy,
            currency_mode=request.currency_mode,
            report_ccy=request.report_ccy,
            fx=request.fx,
            hedging=request.hedging,
        )
    except IndexError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="portfolio_data.daily_data cannot be empty.")

    # 2. Route to the correct engine based on whether a hierarchy is requested
    if request.hierarchy:
        # --- HIERARCHICAL PATH ---
        results, lineage_data = calculate_hierarchical_contribution(request)

        meta = Meta(
            calculation_id=request.calculation_id,
            engine_version=settings.APP_VERSION,
            precision_mode=request.precision_mode,
            calendar=request.calendar,
            annualization=request.annualization,
            periods={
                "type": request.portfolio_data.period_type.value,
                "start": str(twr_config.report_start_date or twr_config.performance_start_date),
                "end": str(twr_config.report_end_date),
            },
            input_fingerprint=input_fingerprint,
            calculation_hash=calculation_hash,
            report_ccy=request.report_ccy,
        )
        # TODO: Plumb diagnostics from hierarchical path
        diagnostics = Diagnostics(nip_days=0, reset_days=0, effective_period_start=twr_config.report_start_date or twr_config.performance_start_date, notes=[])
        audit = Audit(counts={"input_positions": len(request.positions_data)})
        
        response_model = ContributionResponse(
            calculation_id=request.calculation_id,
            portfolio_number=request.portfolio_number,
            report_start_date=request.portfolio_data.report_start_date,
            report_end_date=request.portfolio_data.report_end_date,
            summary=results["summary"],
            levels=results["levels"],
            meta=meta,
            diagnostics=diagnostics,
            audit=audit,
        )

        background_tasks.add_task(
            lineage_service.capture,
            calculation_id=request.calculation_id,
            calculation_type="ContributionHierarchy",
            request_model=request,
            response_model=response_model,
            calculation_details=lineage_data
        )
        return response_model

    # --- SINGLE-LEVEL PATH (EXISTING LOGIC) ---
    try:
        # Recalculate portfolio TWR using base currency values if in FX mode
        portfolio_twr_config = twr_config
        if twr_config.currency_mode == "BOTH":
            portfolio_twr_config = EngineConfig(
                performance_start_date=twr_config.performance_start_date,
                report_start_date=twr_config.report_start_date,
                report_end_date=twr_config.report_end_date,
                metric_basis=twr_config.metric_basis,
                period_type=twr_config.period_type,
                currency_mode="BASE_ONLY" # Ensure no decomposition for base ccy assets
            )
            
        portfolio_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in request.portfolio_data.daily_data])
        portfolio_results, portfolio_diags = run_calculations(portfolio_df, portfolio_twr_config)

        position_results_map = {}
        for position in request.positions_data:
            pos_twr_config = twr_config
            # Create a specific config for this position if it's in a foreign currency
            if request.currency_mode != "BOTH" or position.meta.get("currency") == request.report_ccy:
                 pos_twr_config = EngineConfig(
                    performance_start_date=twr_config.performance_start_date,
                    report_start_date=twr_config.report_start_date,
                    report_end_date=twr_config.report_end_date,
                    metric_basis=twr_config.metric_basis,
                    period_type=twr_config.period_type,
                    currency_mode="BASE_ONLY"
                )

            position_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in position.daily_data])
            position_results, _ = run_calculations(position_df, pos_twr_config)
            position_results_map[position.position_id] = position_results

        contribution_results = calculate_position_contribution(
            portfolio_results, position_results_map, request.smoothing, request.emit, twr_config
        )

        raw_timeseries = contribution_results.pop("timeseries", None)
        total_portfolio_return = ((1 + portfolio_results[PortfolioColumns.DAILY_ROR] / 100).prod() - 1) * 100

        position_contributions = [
            PositionContribution(
                position_id=pos_id,
                total_contribution=data["total_contribution"],
                average_weight=data["average_weight"],
                total_return=data["total_return"],
                local_contribution=data.get("local_contribution"),
                fx_contribution=data.get("fx_contribution"),
            )
            for pos_id, data in contribution_results.items()
        ]
        total_contribution_sum = sum(pc.total_contribution for pc in position_contributions)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during contribution calculation: {str(e)}",
        )

    meta = Meta(
        calculation_id=request.calculation_id,
        engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode,
        calendar=request.calendar,
        annualization=request.annualization,
        periods={
            "type": request.portfolio_data.period_type.value,
            "start": str(twr_config.report_start_date or twr_config.performance_start_date),
            "end": str(twr_config.report_end_date),
        },
        input_fingerprint=input_fingerprint,
        calculation_hash=calculation_hash,
        report_ccy=request.report_ccy,
    )
    diagnostics = Diagnostics(
        nip_days=portfolio_diags.get("nip_days", 0),
        reset_days=portfolio_diags.get("reset_days", 0),
        effective_period_start=portfolio_diags.get("effective_period_start"),
        notes=portfolio_diags.get("notes", []),
        policy=portfolio_diags.get("policy"),
        samples=portfolio_diags.get("samples"),
    )
    audit = Audit(
        sum_of_parts_vs_total_bp=(total_contribution_sum - total_portfolio_return) * 100,
        counts={"input_positions": len(request.positions_data), "calculation_days": len(portfolio_results)},
    )

    response_payload = {
        "calculation_id": request.calculation_id,
        "portfolio_number": request.portfolio_number,
        "report_start_date": request.portfolio_data.report_start_date,
        "report_end_date": request.portfolio_data.report_end_date,
        "total_portfolio_return": total_portfolio_return,
        "total_contribution": total_contribution_sum,
        "position_contributions": position_contributions,
        "meta": meta,
        "diagnostics": diagnostics,
        "audit": audit,
    }

    if request.emit.timeseries and raw_timeseries:
        timeseries = []
        for row in raw_timeseries:
            total_contrib = sum(v for k, v in row.items() if k != "date")
            timeseries.append(DailyContribution(date=row["date"], total_contribution=total_contrib))
        response_payload["timeseries"] = timeseries

    if request.emit.by_position_timeseries and raw_timeseries:
        by_pos_ts = {pos_id: [] for pos_id in position_results_map.keys()}
        for row in raw_timeseries:
            for pos_id in by_pos_ts.keys():
                by_pos_ts[pos_id].append(PositionDailyContribution(date=row["date"], contribution=row.get(pos_id, 0.0)))

        response_payload["by_position_timeseries"] = [
            PositionContributionSeries(position_id=pos_id, series=series) for pos_id, series in by_pos_ts.items()
        ]

    response_model = ContributionResponse.model_validate(response_payload)

    lineage_details = {"portfolio_twr.csv": portfolio_results}
    if raw_timeseries:
        lineage_details["positions_daily_contribution.csv"] = pd.DataFrame(raw_timeseries)

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="Contribution",
        request_model=request,
        response_model=response_model,
        calculation_details=lineage_details,
    )

    return response_model