# app/api/endpoints/performance.py
from fastapi import APIRouter, HTTPException, status
from adapters.api_adapter import create_engine_config, create_engine_dataframe, format_breakdowns_for_response
from app.core.config import get_settings
from app.models.attribution_requests import AttributionRequest
from app.models.attribution_responses import AttributionResponse
from app.models.requests import PerformanceRequest
from app.models.mwr_requests import MoneyWeightedReturnRequest
from app.models.mwr_responses import MoneyWeightedReturnResponse
from app.models.responses import PerformanceResponse
from core.envelope import Audit, Diagnostics, Meta
from engine.attribution import run_attribution_calculations
from engine.breakdown import generate_performance_breakdowns
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
from engine.mwr import calculate_money_weighted_return

router = APIRouter()
settings = get_settings()


@router.post("/twr", response_model=PerformanceResponse, summary="Calculate Time-Weighted Return")
async def calculate_twr_endpoint(request: PerformanceRequest):
    """
    Calculates time-weighted return (TWR) and provides performance breakdowns
    by requested frequencies (daily, monthly, yearly, etc.).
    """
    try:
        engine_config = create_engine_config(request)
        engine_df = create_engine_dataframe([item.model_dump(by_alias=True) for item in request.daily_data])

        daily_results_df, diagnostics_data = run_calculations(engine_df, engine_config)

        breakdowns_data = generate_performance_breakdowns(
            daily_results_df,
            request.frequencies,
            request.annualization,
            request.output.include_cumulative,
        )
        formatted_breakdowns = format_breakdowns_for_response(
            breakdowns_data, daily_results_df, request.flags.compat_legacy_names
        )

    except InvalidEngineInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Input: {e.message}")
    except EngineCalculationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
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
        periods={"type": request.period_type.value, "start": str(engine_config.report_start_date or engine_config.performance_start_date), "end": str(engine_config.report_end_date)},
    )
    diagnostics = Diagnostics(
        nip_days=diagnostics_data.get("nip_days", 0),
        reset_days=diagnostics_data.get("reset_days", 0),
        effective_period_start=diagnostics_data.get("effective_period_start"),
        notes=diagnostics_data.get("notes", []),
    )
    audit = Audit(counts={"input_rows": len(request.daily_data), "output_rows": len(daily_results_df)})

    response_payload = {
        "calculation_id": request.calculation_id,
        "portfolio_number": request.portfolio_number,
        "breakdowns": formatted_breakdowns,
        "meta": meta,
        "diagnostics": diagnostics,
        "audit": audit,
    }

    if request.reset_policy.emit and diagnostics_data.get("resets"):
        response_payload["reset_events"] = diagnostics_data["resets"]

    return PerformanceResponse.model_validate(response_payload)


@router.post("/mwr", response_model=MoneyWeightedReturnResponse, summary="Calculate Money-Weighted Return")
async def calculate_mwr_endpoint(request: MoneyWeightedReturnRequest):
    """
    Calculates the money-weighted return (MWR) for a portfolio over a given period.
    """
    try:
        mwr_result = calculate_money_weighted_return(
            beginning_mv=request.beginning_mv,
            ending_mv=request.ending_mv,
            cash_flows=request.cash_flows,
            calculation_method=request.mwr_method,
            annualization=request.annualization,
            as_of=request.as_of,
        )
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
        **mwr_result.model_dump(),
        "meta": meta,
        "diagnostics": diagnostics,
        "audit": audit,
    }

    return MoneyWeightedReturnResponse.model_validate(response_payload)


@router.post("/attribution", response_model=AttributionResponse, summary="Calculate Multi-Level Performance Attribution")
async def calculate_attribution_endpoint(request: AttributionRequest):
    """
    Calculates multi-level, Brinson-style performance attribution, decomposing
    active return into allocation, selection, and interaction effects.
    """
    try:
        response = run_attribution_calculations(request)
        return response
    except (InvalidEngineInputError, ValueError, NotImplementedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EngineCalculationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}",
        )