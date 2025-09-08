# app/api/endpoints/performance.py
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
import pandas as pd
from adapters.api_adapter import create_engine_config, create_engine_dataframe, format_breakdowns_for_response
from app.core.config import get_settings
from app.models.attribution_requests import AttributionRequest
from app.models.attribution_responses import AttributionResponse
from app.models.requests import PerformanceRequest
from app.models.mwr_requests import MoneyWeightedReturnRequest
from app.models.mwr_responses import MoneyWeightedReturnResponse
from app.models.responses import PerformanceResponse
from app.services.lineage_service import lineage_service
from core.envelope import Audit, Diagnostics, Meta
from core.repro import generate_canonical_hash
from engine.attribution import run_attribution_calculations
from engine.breakdown import generate_performance_breakdowns
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
from engine.mwr import calculate_money_weighted_return

router = APIRouter()
settings = get_settings()


@router.post("/twr", response_model=PerformanceResponse, summary="Calculate Time-Weighted Return")
async def calculate_twr_endpoint(request: PerformanceRequest, background_tasks: BackgroundTasks):
    """
    Calculates time-weighted return (TWR) and provides performance breakdowns
    by requested frequencies (daily, monthly, yearly, etc.).
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)
    
    try:
        engine_config = create_engine_config(request)
        engine_df = create_engine_dataframe([item.model_dump() for item in request.daily_data])

        daily_results_df, diagnostics_data = run_calculations(engine_df, engine_config)

        breakdowns_data = generate_performance_breakdowns(
            daily_results_df,
            request.frequencies,
            request.annualization,
            request.output.include_cumulative,
        )
        formatted_breakdowns = format_breakdowns_for_response(
            breakdowns_data, daily_results_df
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
        input_fingerprint=input_fingerprint,
        calculation_hash=calculation_hash,
    )
    diagnostics = Diagnostics(
        nip_days=diagnostics_data.get("nip_days", 0),
        reset_days=diagnostics_data.get("reset_days", 0),
        effective_period_start=diagnostics_data.get("effective_period_start"),
        notes=diagnostics_data.get("notes", []),
        policy=diagnostics_data.get("policy"),
        samples=diagnostics_data.get("samples"),
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

    response_model = PerformanceResponse.model_validate(response_payload)

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="TWR",
        request_model=request,
        response_model=response_model,
        calculation_details={"twr_calculation_details.csv": daily_results_df}
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

    # Create DataFrame for lineage capture
    lineage_df_data = [{"date": str(request.as_of), "type": "begin_mv", "amount": request.begin_mv}]
    lineage_df_data.extend([{"date": str(cf.date), "type": "cash_flow", "amount": cf.amount} for cf in request.cash_flows])
    lineage_df_data.append({"date": str(request.as_of), "type": "end_mv", "amount": request.end_mv})
    lineage_df = pd.DataFrame(lineage_df_data)

    background_tasks.add_task(
        lineage_service.capture,
        calculation_id=request.calculation_id,
        calculation_type="MWR",
        request_model=request,
        response_model=response_model,
        calculation_details={"mwr_cashflow_schedule.csv": lineage_df}
    )

    return response_model


@router.post("/attribution", response_model=AttributionResponse, summary="Calculate Multi-Level Performance Attribution")
async def calculate_attribution_endpoint(request: AttributionRequest, background_tasks: BackgroundTasks):
    """
    Calculates multi-level, Brinson-style performance attribution, decomposing
    active return into allocation, selection, and interaction effects.
    """
    input_fingerprint, calculation_hash = generate_canonical_hash(request, settings.APP_VERSION)
    
    try:
        response = run_attribution_calculations(request)
        
        # Add hash to meta if it exists, otherwise create it
        if response.meta:
            response.meta.input_fingerprint = input_fingerprint
            response.meta.calculation_hash = calculation_hash
        else:
            # Placeholder meta if engine doesn't create one
             response.meta = Meta(
                calculation_id=request.calculation_id,
                engine_version=settings.APP_VERSION,
                precision_mode=request.precision_mode,
                annualization=request.annualization,
                calendar=request.calendar,
                periods={},
                input_fingerprint=input_fingerprint,
                calculation_hash=calculation_hash
            )
        
        # Placeholder for detailed attribution dataframes
        background_tasks.add_task(
            lineage_service.capture,
            calculation_id=request.calculation_id,
            calculation_type="Attribution",
            request_model=request,
            response_model=response,
            calculation_details={}
        )
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