# app/api/endpoints/performance.py
from fastapi import APIRouter, HTTPException, status
from adapters.api_adapter import (
    create_engine_config,
    create_engine_dataframe,
    format_engine_output,
    format_summary_for_response,
)
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceResponse
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError

router = APIRouter()


@router.post("/twr", response_model=PerformanceResponse, summary="Calculate Time-Weighted Return")
async def calculate_twr_endpoint(request: PerformanceRequest):
    """
    Calculates time-weighted return (TWR) with daily granularity based on a time series of portfolio data.
    """
    if not request.daily_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="daily_data must be provided in the request body.",
        )

    try:
        engine_config = create_engine_config(request)
        daily_data_dicts = [item.model_dump(by_alias=True, exclude_unset=True) for item in request.daily_data]
        engine_df = create_engine_dataframe(daily_data_dicts)

        results_df = run_calculations(engine_df, engine_config)

        daily_performance, summary_data = format_engine_output(results_df, engine_config)
        summary_performance = format_summary_for_response(summary_data, engine_config)

    except InvalidEngineInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Input: {e.message}")
    except EngineCalculationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}",
        )

    return PerformanceResponse(
        portfolio_number=request.portfolio_number,
        performance_start_date=request.performance_start_date,
        metric_basis=request.metric_basis,
        period_type=request.period_type,
        calculated_daily_performance=daily_performance,
        summary_performance=summary_performance,
    )


@router.post("/mwr", summary="Calculate Money-Weighted Return (Placeholder)")
async def calculate_mwr_endpoint():
    """
    (Placeholder) Calculates the money-weighted return (MWR) for a portfolio over a given period.
    """
    return {"message": "MWR endpoint is not yet implemented."}