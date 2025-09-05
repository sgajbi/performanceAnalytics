# app/api/endpoints/performance.py
from fastapi import APIRouter, HTTPException, status
from adapters.api_adapter import create_engine_config, create_engine_dataframe, format_breakdowns_for_response
from app.models.requests import PerformanceRequest
from app.models.mwr_requests import MoneyWeightedReturnRequest
from app.models.mwr_responses import MoneyWeightedReturnResponse
from app.models.responses import PerformanceResponse
from engine.breakdown import generate_performance_breakdowns
from engine.compute import run_calculations
from engine.exceptions import EngineCalculationError, InvalidEngineInputError
from engine.mwr import calculate_money_weighted_return

router = APIRouter()


@router.post("/twr", response_model=PerformanceResponse, summary="Calculate Time-Weighted Return")
async def calculate_twr_endpoint(request: PerformanceRequest):
    """
    Calculates time-weighted return (TWR) and provides performance breakdowns
    by requested frequencies (daily, monthly, yearly, etc.).
    """
    try:
        engine_config = create_engine_config(request)
        engine_df = create_engine_dataframe(
            [item.model_dump(by_alias=True) for item in request.daily_data]
        )
        daily_results_df = run_calculations(engine_df, engine_config)
        breakdowns_data = generate_performance_breakdowns(daily_results_df, request.frequencies)
        formatted_breakdowns = format_breakdowns_for_response(breakdowns_data, daily_results_df)
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
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        breakdowns=formatted_breakdowns,
    )


@router.post("/mwr", response_model=MoneyWeightedReturnResponse, summary="Calculate Money-Weighted Return")
async def calculate_mwr_endpoint(request: MoneyWeightedReturnRequest):
    """
    Calculates the money-weighted return (MWR) for a portfolio over a given period.
    """
    try:
        cash_flows_dict = [cf.model_dump() for cf in request.cash_flows]
        mwr = calculate_money_weighted_return(
            beginning_mv=request.beginning_mv,
            ending_mv=request.ending_mv,
            cash_flows=cash_flows_dict
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during MWR calculation: {str(e)}",
        )

    return MoneyWeightedReturnResponse(
        calculation_id=request.calculation_id,
        portfolio_number=request.portfolio_number,
        money_weighted_return=mwr,
    )