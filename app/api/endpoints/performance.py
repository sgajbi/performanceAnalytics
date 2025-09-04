# app/api/endpoints/performance.py

from fastapi import APIRouter, HTTPException, status
from app.core.exceptions import (
    CalculationLogicError,
    InvalidInputDataError,
    PerformanceCalculatorError,
)
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceResponse
from adapters.api_adapter import (
    create_engine_config,
    create_engine_dataframe,
    format_engine_output,
    format_summary_for_response,
)
from engine.compute import run_calculations

router = APIRouter()


@router.post("/calculate_performance", response_model=PerformanceResponse)
async def calculate_performance_endpoint(request: PerformanceRequest):
    """
    Calculates portfolio performance based on the provided inputs and daily time series data.
    The daily data is now part of the request payload.
    """
    if not request.daily_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="daily_data must be provided in the request body.",
        )

    try:
        # 1. Create engine config and dataframe using the adapter
        engine_config = create_engine_config(request)
        daily_data_dicts = [
            item.model_dump(by_alias=True, exclude_unset=True)
            for item in request.daily_data
        ]
        engine_df = create_engine_dataframe(daily_data_dicts)

        # 2. Run the core calculation engine
        results_df = run_calculations(engine_df, engine_config)

        # 3. Format the engine output back to the API response structure
        daily_performance, summary_data = format_engine_output(
            results_df, engine_config
        )
        summary_performance = format_summary_for_response(
            summary_data, engine_config
        )

    except InvalidInputDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Input: {e.message}"
        )
    except CalculationLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation Error: {e.message}",
        )
    except PerformanceCalculatorError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected calculator error occurred: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}",
        )

    # Construct the final Pydantic response model
    return PerformanceResponse(
        portfolio_number=request.portfolio_number,
        performance_start_date=request.performance_start_date,
        metric_basis=request.metric_basis,
        period_type=request.period_type,
        calculated_daily_performance=daily_performance,
        summary_performance=summary_performance,
    )