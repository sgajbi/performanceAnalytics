# app/api/endpoints/performance.py

from datetime import date

from fastapi import APIRouter, HTTPException, status  # Import status for better HTTP error codes

from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    FINAL_CUMULATIVE_ROR_PERCENT_FIELD,
    MGMT_FEES_FIELD,
    NCTRL_1_FIELD,
    NCTRL_2_FIELD,
    NCTRL_3_FIELD,
    NCTRL_4_FIELD,
    NIP_FIELD,
    PERF_DATE_FIELD,
    PERF_RESET_FIELD,
)
from app.core.exceptions import (
    CalculationLogicError,
    InvalidInputDataError,
    MissingConfigurationError,
    PerformanceCalculatorError,
)
from app.models.requests import DailyInputData, PerformanceRequest
from app.models.responses import DailyPerformance, PerformanceResponse, SummaryPerformance
from app.services.calculator import PortfolioPerformanceCalculator

router = APIRouter()


@router.post("/calculate_performance", response_model=PerformanceResponse)
async def calculate_performance_endpoint(request: PerformanceRequest):
    """
    Calculates portfolio performance based on the provided inputs and daily time series data.
    The daily data is now part of the request payload.
    """
    daily_data = request.daily_data
    if not daily_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="daily_data must be provided in the request body."
        )

    config = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date.strftime("%Y-%m-%d"),
        "metric_basis": request.metric_basis,
        "report_start_date": request.report_start_date.strftime("%Y-%m-%d") if request.report_start_date else None,
        "report_end_date": request.report_end_date.strftime("%Y-%m-%d"),
        "period_type": request.period_type,
    }

    try:
        calculator = PortfolioPerformanceCalculator(config)
        calculated_results = calculator.calculate_performance(
            [item.model_dump(by_alias=True, exclude_unset=True) for item in daily_data], config
        )

        # ✅ Use new summary method from calculator
        summary_performance = calculator.get_summary_performance(calculated_results)

    except InvalidInputDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Input: {e.message}")
    except MissingConfigurationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Configuration Error: {e.message}")
    except CalculationLogicError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Calculation Error: {e.message}")
    except PerformanceCalculatorError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected calculator error occurred: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {str(e)}"
        )

    response_data = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date,
        "metric_basis": request.metric_basis,
        "period_type": request.period_type,
        "calculated_daily_performance": calculated_results,
        "summary_performance": summary_performance,
    }

    return response_data
