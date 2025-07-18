# app/api/endpoints/performance.py

from fastapi import APIRouter, HTTPException
from app.models.requests import PerformanceRequest, DailyInputData # Import updated request model
from app.models.responses import DailyPerformance, SummaryPerformance, PerformanceResponse # Import response models
from app.services.calculator import PortfolioPerformanceCalculator # Corrected import path
from datetime import date # Keep date for type hinting
from app.core.constants import ( #
    PERF_DATE_FIELD, BEGIN_MARKET_VALUE_FIELD, BOD_CASHFLOW_FIELD,
    EOD_CASHFLOW_FIELD, MGMT_FEES_FIELD, END_MARKET_VALUE_FIELD,
    NCTRL_1_FIELD, NCTRL_2_FIELD, NCTRL_3_FIELD, NCTRL_4_FIELD,
    PERF_RESET_FIELD, NIP_FIELD, FINAL_CUMULATIVE_ROR_PERCENT_FIELD
)
 
router = APIRouter()

@router.post("/calculate_performance", response_model=PerformanceResponse)
async def calculate_performance_endpoint(request: PerformanceRequest): #
    """
    Calculates portfolio performance based on the provided inputs and daily time series data.
    The daily data is now part of the request payload.
    """
    # daily_data is now directly available from the request object
    daily_data = request.daily_data
    if not daily_data:
        raise HTTPException(status_code=400, detail="daily_data must be provided in the request body.")

    # Prepare config for the calculator from the request
    # Ensure dates are formatted as strings for the calculator's constructor, which expects them.
    config = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date.strftime("%Y-%m-%d"),
        "metric_basis": request.metric_basis, #
        "report_start_date": request.report_start_date.strftime("%Y-%m-%d") if request.report_start_date else None,
        "report_end_date": request.report_end_date.strftime("%Y-%m-%d"),
        "period_type": request.period_type
    }

    try:
        calculator = PortfolioPerformanceCalculator(config)
        # Pass the daily_data list directly to the calculator
        calculated_results = calculator.calculate_performance(
            [item.model_dump(by_alias=True, exclude_unset=True) for item in daily_data], config #
        )

        summary_performance = {}
        # Ensure there are results to summarize, and that report_end_date is valid
        if calculated_results and request.report_end_date:
            # Find the first day within the report period
            first_day_in_report = next((day for day in calculated_results if date.fromisoformat(day[PERF_DATE_FIELD]) >= (request.report_start_date if request.report_start_date else date.min)), None) #
            # Find the last day within the report period
            last_day_in_report = next((day for day in reversed(calculated_results) if date.fromisoformat(day[PERF_DATE_FIELD]) <= request.report_end_date), None) #

            if first_day_in_report and last_day_in_report:
                summary_performance["report_start_date"] = config.get("report_start_date") #
                summary_performance["report_end_date"] = config.get("report_end_date") #
                summary_performance[BEGIN_MARKET_VALUE_FIELD] = first_day_in_report.get(BEGIN_MARKET_VALUE_FIELD, 0.0) #
                summary_performance[END_MARKET_VALUE_FIELD] = last_day_in_report.get(END_MARKET_VALUE_FIELD, 0.0) #

                # Sum up cashflows and fees, and check flags for the entire calculated period
                total_bod_cf = 0.0 #
                total_eod_cf = 0.0
                total_mgmt_fees = 0.0

                # Flags that should be 1 if TRUE for any day in the period
                summary_nctrl1 = 0 #
                summary_nctrl2 = 0
                summary_nctrl3 = 0
                summary_nctrl4 = 0
                summary_perf_reset = 0
                summary_nip = 0 #


                for day_data in calculated_results: # Iterate through all calculated_results
                    current_date = date.fromisoformat(day_data[PERF_DATE_FIELD]) #
                    # Only sum cashflows/fees and check flags for days within the report_start_date and report_end_date
                    if (request.report_start_date is None or current_date >= request.report_start_date) and \
                       current_date <= request.report_end_date: #
                        total_bod_cf += day_data.get(BOD_CASHFLOW_FIELD, 0.0) #
                        total_eod_cf += day_data.get(EOD_CASHFLOW_FIELD, 0.0)
                        total_mgmt_fees += day_data.get(MGMT_FEES_FIELD, 0.0)

                        if day_data.get(NCTRL_1_FIELD) == 1: #
                            summary_nctrl1 = 1
                        if day_data.get(NCTRL_2_FIELD) == 1: #
                            summary_nctrl2 = 1
                        if day_data.get(NCTRL_3_FIELD) == 1: #
                            summary_nctrl3 = 1
                        if day_data.get(NCTRL_4_FIELD) == 1: #
                            summary_nctrl4 = 1
                        if day_data.get(PERF_RESET_FIELD) == 1: #
                            summary_perf_reset = 1
                        if day_data.get(NIP_FIELD) == 1: #
                            summary_nip = 1

                summary_performance[BOD_CASHFLOW_FIELD] = total_bod_cf #
                summary_performance[EOD_CASHFLOW_FIELD] = total_eod_cf #
                summary_performance[MGMT_FEES_FIELD] = total_mgmt_fees
                summary_performance[FINAL_CUMULATIVE_ROR_PERCENT_FIELD] = last_day_in_report.get(FINAL_CUMULATIVE_ROR_PERCENT_FIELD, 0.0)

                summary_performance[NCTRL_1_FIELD] = summary_nctrl1 #
                summary_performance[NCTRL_2_FIELD] = summary_nctrl2 #
                summary_performance[NCTRL_3_FIELD] = summary_nctrl3 #
                summary_performance[NCTRL_4_FIELD] = summary_nctrl4
                summary_performance[PERF_RESET_FIELD] = summary_perf_reset
                summary_performance[NIP_FIELD] = summary_nip #
            else: # If no data points fall within the report range #
                summary_performance = { #
                    "report_start_date": config.get("report_start_date"), #
                    "report_end_date": config.get("report_end_date"),
                    BEGIN_MARKET_VALUE_FIELD: 0.0, #
                    BOD_CASHFLOW_FIELD: 0.0,
                    EOD_CASHFLOW_FIELD: 0.0, #
                    MGMT_FEES_FIELD: 0.0,
                    END_MARKET_VALUE_FIELD: 0.0, #
                    FINAL_CUMULATIVE_ROR_PERCENT_FIELD: 0.0,
                    NCTRL_1_FIELD: 0,
                    NCTRL_2_FIELD: 0, #
                    NCTRL_3_FIELD: 0, #
                    NCTRL_4_FIELD: 0,
                    PERF_RESET_FIELD: 0,
                    NIP_FIELD: 0 #
                }

    except Exception as e: #
        raise HTTPException(status_code=500, detail=f"Error during performance calculation: {str(e)}")

    # Prepare the response data, ensuring field names match Pydantic model aliases
    response_data = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date,
        "metric_basis": request.metric_basis,
        "period_type": request.period_type,
        "calculated_daily_performance": calculated_results, #
        "summary_performance": summary_performance #
    }

    return response_data #