# app/api/endpoints/performance.py
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from adapters.api_adapter import (
    create_engine_config,
    create_engine_dataframe,
    format_breakdowns_for_response,
)
from app.core.config import get_settings
from app.models.attribution_requests import AttributionRequest
from app.models.attribution_responses import AttributionResponse
from app.models.mwr_requests import MoneyWeightedReturnRequest
from app.models.mwr_responses import MoneyWeightedReturnResponse
from app.models.pas_connected_requests import PasInputTwrRequest
from app.models.pas_connected_responses import (
    PasInputPeriodResult,
    PasInputTwrResponse,
)
from app.models.requests import PerformanceRequest
from app.models.responses import (
    PerformanceResponse,
    PortfolioReturnDecomposition,
    ResetEvent,
    SinglePeriodPerformanceResult,
)
from app.services.lineage_service import lineage_service
from app.services.pas_snapshot_service import PasSnapshotService
from core.envelope import Audit, Diagnostics, Meta
from core.periods import resolve_periods
from core.repro import generate_canonical_hash
from engine.attribution import aggregate_attribution_results, run_attribution_calculations
from engine.breakdown import generate_performance_breakdowns
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
from engine.mwr import calculate_money_weighted_return
from engine.schema import PortfolioColumns

router = APIRouter(tags=["Performance"])
settings = get_settings()


@router.post(
    "/twr/pas-input",
    response_model=PasInputTwrResponse,
    summary="Calculate TWR from PAS raw performance input contract",
    description=(
        "Computes PA-owned TWR analytics from PAS-provided raw valuation input series. "
        "PAS acts as data provider; PA remains analytics authority."
    ),
    responses={
        200: {"description": "PA TWR result computed from PAS input contract."},
        404: {"description": "Requested periods not available for the requested as-of context."},
        502: {"description": "Invalid PAS payload for PA analytics computation."},
    },
)
async def calculate_twr_from_pas_input(request: PasInputTwrRequest):
    """
    Retrieves PAS raw performance input series and computes PA-owned TWR analytics.
    PAS acts as data provider only; performance metrics are computed in PA.
    """
    pas_service = PasSnapshotService(
        base_url=settings.PAS_QUERY_BASE_URL,
        timeout_seconds=settings.PAS_TIMEOUT_SECONDS,
    )
    upstream_status, upstream_payload = await pas_service.get_performance_input(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date,
        lookback_days=request.lookback_days,
        consumer_system=request.consumer_system,
    )
    if upstream_status >= status.HTTP_400_BAD_REQUEST:
        raise HTTPException(status_code=upstream_status, detail=str(upstream_payload))

    valuation_points = upstream_payload.get("valuationPoints")
    if not isinstance(valuation_points, list) or not valuation_points:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid PAS performance input payload: missing valuationPoints.",
        )

    performance_start_date = upstream_payload.get("performanceStartDate")
    if not isinstance(performance_start_date, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid PAS performance input payload: missing performanceStartDate.",
        )

    requested_periods = request.periods or ["YTD"]
    analyses = [{"period": period_key, "frequencies": ["monthly"]} for period_key in requested_periods]
    try:
        performance_request = PerformanceRequest.model_validate(
            {
                "portfolio_number": upstream_payload.get("portfolioId", request.portfolio_id),
                "performance_start_date": performance_start_date,
                "metric_basis": "NET",
                "report_end_date": str(request.as_of_date),
                "analyses": analyses,
                "valuation_points": valuation_points,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid PAS performance input payload: {exc}",
        ) from exc

    computed = await calculate_twr_endpoint(performance_request, BackgroundTasks())
    results_by_period: dict[str, PasInputPeriodResult] = {}
    for period_key in requested_periods:
        period_result = computed.results_by_period.get(period_key)
        if period_result is None:
            continue
        summary = None
        for items in period_result.breakdowns.values():
            if items:
                summary = items[-1].summary
                break
        if summary is None:
            continue
        results_by_period[period_key] = PasInputPeriodResult(
            period=period_key,
            start_date=None,
            end_date=None,
            net_cumulative_return=summary.period_return_pct,
            net_annualized_return=summary.annualized_return_pct,
            gross_cumulative_return=None,
            gross_annualized_return=None,
        )

    if not results_by_period:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested periods not found.")

    return PasInputTwrResponse(
        portfolio_number=performance_request.portfolio_number,
        as_of_date=request.as_of_date,
        pasContractVersion=upstream_payload.get("contractVersion", "v1"),
        consumerSystem=upstream_payload.get("consumerSystem", request.consumer_system),
        resultsByPeriod=results_by_period,
    )


@router.post("/twr", response_model=PerformanceResponse, summary="Calculate Time-Weighted Return")
async def calculate_twr_endpoint(request: PerformanceRequest, background_tasks: BackgroundTasks):
    """
    Calculates time-weighted return (TWR) for one or more requested periods
    and provides performance breakdowns by requested frequencies.
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)

    try:
        periods_to_resolve = [analysis.period for analysis in request.analyses]
        freqs_by_period = {analysis.period.value: analysis.frequencies for analysis in request.analyses}

        as_of_date = request.report_end_date
        resolved_periods = resolve_periods(periods_to_resolve, as_of_date, request.performance_start_date)

        if not resolved_periods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid periods could be resolved.")

        master_start_date = min(p.start_date for p in resolved_periods)
        master_end_date = max(p.end_date for p in resolved_periods)

        engine_config = create_engine_config(request, master_start_date, master_end_date)
        engine_df = create_engine_dataframe([item.model_dump() for item in request.valuation_points])
        daily_results_df, diagnostics_data = run_calculations(engine_df, engine_config)

        results_by_period = {}
        daily_results_df[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(
            daily_results_df[PortfolioColumns.PERF_DATE.value]
        ).dt.date

        def get_total_cum_ror(row: pd.Series, prefix: str = "") -> float:
            if row is None:
                return 0.0
            long_cum = row.get(f"{prefix}long_cum_ror", 0.0)
            short_cum = row.get(f"{prefix}short_cum_ror", 0.0)
            return ((1 + long_cum / 100) * (1 + short_cum / 100) - 1) * 100

        def get_total_return_from_slice(df_slice: pd.DataFrame) -> PortfolioReturnDecomposition:
            if df_slice.empty:
                return PortfolioReturnDecomposition(local=0.0, fx=0.0, base=0.0)

            if df_slice[PortfolioColumns.PERF_RESET.value].any():
                end_row = df_slice.iloc[-1]
                full_perf_dates = pd.to_datetime(daily_results_df[PortfolioColumns.PERF_DATE.value]).dt.date
                slice_min_date = pd.to_datetime(df_slice[PortfolioColumns.PERF_DATE.value].min()).date()
                day_before_mask = full_perf_dates < slice_min_date
                day_before_row = daily_results_df[day_before_mask].iloc[-1] if day_before_mask.any() else None

                start_cum_base = (
                    day_before_row[PortfolioColumns.FINAL_CUM_ROR.value] if day_before_row is not None else 0.0
                )
                end_cum_base = end_row[PortfolioColumns.FINAL_CUM_ROR.value]

                start_base_denom = 1 + start_cum_base / 100
                if start_base_denom == 0:
                    base_total = end_cum_base
                else:
                    base_total = (((1 + end_cum_base / 100) / start_base_denom) - 1) * 100

                if "local_ror" in df_slice.columns:
                    start_cum_local = get_total_cum_ror(day_before_row, "local_ror_")
                    end_cum_local = get_total_cum_ror(end_row, "local_ror_")

                    start_local_denom = 1 + start_cum_local / 100
                    if start_local_denom == 0:
                        local_total = end_cum_local
                    else:
                        local_total = (((1 + end_cum_local / 100) / start_local_denom) - 1) * 100

                    base_denom_for_fx = 1 + local_total / 100
                    if base_denom_for_fx == 0:
                        fx_total = 0.0
                    else:
                        fx_total = (((1 + base_total / 100) / base_denom_for_fx) - 1) * 100
                else:
                    local_total = base_total
                    fx_total = 0.0
            else:
                base_total = ((1 + df_slice[PortfolioColumns.DAILY_ROR.value] / 100).prod() - 1) * 100
                if "local_ror" in df_slice.columns:
                    local_total = ((1 + df_slice["local_ror"] / 100).prod() - 1) * 100
                    base_denom_for_fx = 1 + local_total / 100
                    if base_denom_for_fx == 0:
                        fx_total = 0.0
                    else:
                        fx_total = (((1 + base_total / 100) / base_denom_for_fx) - 1) * 100
                else:
                    local_total = base_total
                    fx_total = 0.0

            return PortfolioReturnDecomposition(local=local_total, fx=fx_total, base=base_total)

        for period in resolved_periods:
            period_slice_df = daily_results_df[
                (daily_results_df[PortfolioColumns.PERF_DATE.value] >= period.start_date)
                & (daily_results_df[PortfolioColumns.PERF_DATE.value] <= period.end_date)
            ].copy()

            if period_slice_df.empty:
                continue

            requested_frequencies_for_period = freqs_by_period.get(period.name, [])
            breakdowns_data = generate_performance_breakdowns(
                period_slice_df,
                requested_frequencies_for_period,
                request.annualization,
                request.output.include_cumulative,
                request.rounding_precision,
            )
            formatted_breakdowns = format_breakdowns_for_response(
                breakdowns_data, period_slice_df, request.output.include_timeseries
            )

            period_return_summary = get_total_return_from_slice(period_slice_df)
            period_result = SinglePeriodPerformanceResult(
                breakdowns=formatted_breakdowns, portfolio_return=period_return_summary
            )

            if request.reset_policy.emit and diagnostics_data.get("resets"):
                period_result.reset_events = [
                    ResetEvent(**event)
                    for event in diagnostics_data["resets"]
                    if period.start_date <= event["date"] <= period.end_date
                ]

            results_by_period[period.name] = period_result

    except InvalidEngineInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Input: {e.message}")
    except EngineCalculationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}",
        )

    meta = Meta(
        calculation_id=request.calculation_id,
        engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode,
        calendar=request.calendar,
        annualization=request.annualization,
        periods={
            "requested": [p.value for p in periods_to_resolve],
            "master_start": str(master_start_date),
            "master_end": str(master_end_date),
        },
        input_fingerprint=input_fingerprint,
        calculation_hash=calculation_hash,
        report_ccy=engine_config.report_ccy,
    )
    diagnostics = Diagnostics(
        nip_days=diagnostics_data.get("nip_days", 0),
        reset_days=diagnostics_data.get("reset_days", 0),
        effective_period_start=diagnostics_data.get("effective_period_start"),
        notes=diagnostics_data.get("notes", []),
        policy=diagnostics_data.get("policy"),
        samples=diagnostics_data.get("samples"),
    )
    audit = Audit(counts={"input_rows": len(request.valuation_points), "output_rows": len(daily_results_df)})

    response_model = PerformanceResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        results_by_period=results_by_period,
        meta=meta,
        diagnostics=diagnostics,
        audit=audit,
    )

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="TWR",
        request_model=request,
        response_model=response_model,
        calculation_details={"twr_calculation_details.csv": daily_results_df},
    )

    return response_model


@router.post("/mwr", response_model=MoneyWeightedReturnResponse, summary="Calculate Money-Weighted Return")
async def calculate_mwr_endpoint(request: MoneyWeightedReturnRequest, background_tasks: BackgroundTasks):
    """Calculates the money-weighted return (MWR) for a portfolio over a given period."""
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)

    try:
        mwr_result = calculate_money_weighted_return(
            begin_mv=request.begin_mv,
            end_mv=request.end_mv,
            cash_flows=request.cash_flows,
            calculation_method=request.mwr_method,
            annualization=request.annualization,
            as_of=request.as_of,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during MWR calculation: {str(e)}",
        )

    meta = Meta(
        calculation_id=request.calculation_id,
        engine_version=settings.APP_VERSION,
        precision_mode=request.precision_mode,
        annualization=request.annualization,
        calendar=request.calendar,
        periods={"type": "EXPLICIT", "start": str(mwr_result.start_date), "end": str(mwr_result.end_date)},
        input_fingerprint=input_fingerprint,
        calculation_hash=calculation_hash,
    )
    diagnostics = Diagnostics(
        nip_days=0,
        reset_days=0,
        effective_period_start=mwr_result.start_date,
        notes=mwr_result.notes,
    )
    audit = Audit(counts={"cashflows": len(request.cash_flows)})

    response_payload = {
        "calculation_id": request.calculation_id,
        "portfolio_number": request.portfolio_number,
        "money_weighted_return": mwr_result.mwr,
        "mwr_annualized": mwr_result.mwr_annualized,
        "method": mwr_result.method,
        "start_date": mwr_result.start_date,
        "end_date": mwr_result.end_date,
        "notes": mwr_result.notes,
        "convergence": mwr_result.convergence,
        "meta": meta,
        "diagnostics": diagnostics,
        "audit": audit,
    }

    response_model = MoneyWeightedReturnResponse.model_validate(response_payload)

    lineage_df_data = [{"date": str(request.as_of), "type": "begin_mv", "amount": request.begin_mv}]
    lineage_df_data.extend(
        [{"date": str(cf.date), "type": "cash_flow", "amount": cf.amount} for cf in request.cash_flows]
    )
    lineage_df_data.append({"date": str(request.as_of), "type": "end_mv", "amount": request.end_mv})
    lineage_df = pd.DataFrame(lineage_df_data)

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="MWR",
        request_model=request,
        response_model=response_model,
        calculation_details={"mwr_cashflow_schedule.csv": lineage_df},
    )

    return response_model


@router.post(
    "/attribution", response_model=AttributionResponse, summary="Calculate Multi-Level Performance Attribution"
)
async def calculate_attribution_endpoint(request: AttributionRequest, background_tasks: BackgroundTasks):
    """
    Calculates multi-level, Brinson-style performance attribution, decomposing
    active return into allocation, selection, and interaction effects.
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)

    try:
        periods_to_resolve = [analysis.period for analysis in request.analyses]
        resolved_periods = resolve_periods(periods_to_resolve, request.report_end_date, request.report_start_date)

        if not resolved_periods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid periods could be resolved.")

        master_start_date = min(p.start_date for p in resolved_periods)
        master_end_date = max(p.end_date for p in resolved_periods)

        master_request = request.model_copy(deep=True)
        master_request.report_start_date = master_start_date
        master_request.report_end_date = master_end_date

        effects_df, lineage_data = run_attribution_calculations(master_request)

        results_by_period = {}
        for period in resolved_periods:
            period_slice_df = effects_df[
                (effects_df.index.get_level_values("date") >= pd.to_datetime(period.start_date))
                & (effects_df.index.get_level_values("date") <= pd.to_datetime(period.end_date))
            ].copy()

            if period_slice_df.empty:
                continue

            period_result, aggregation_lineage = aggregate_attribution_results(period_slice_df, request)
            if aggregation_lineage:
                lineage_data.update({f"{period.name}_{k}": v for k, v in aggregation_lineage.items()})
            results_by_period[period.name] = period_result

        meta = Meta(
            calculation_id=request.calculation_id,
            engine_version=settings.APP_VERSION,
            precision_mode=request.precision_mode,
            annualization=request.annualization,
            calendar=request.calendar,
            periods={
                "requested": [p.value for p in periods_to_resolve],
                "master_start": str(master_start_date),
                "master_end": str(master_end_date),
            },
            input_fingerprint=input_fingerprint,
            calculation_hash=calculation_hash,
        )

        response_model = AttributionResponse(
            calculation_id=request.calculation_id,
            portfolio_number=request.portfolio_number,
            model=request.model,
            linking=request.linking,
            results_by_period=results_by_period,
            meta=meta,
        )

        background_tasks.add_task(
            lineage_service.capture,
            calculation_id=request.calculation_id,
            calculation_type="Attribution",
            request_model=request,
            response_model=response_model,
            calculation_details=lineage_data,
        )
        return response_model
    except (InvalidEngineInputError, ValueError, NotImplementedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EngineCalculationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}",
        )
