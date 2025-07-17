from fastapi import APIRouter, HTTPException
from app.models.requests import PerformanceRequest, DailyInputData # Import updated request model
from app.models.responses import DailyPerformance, SummaryPerformance, PerformanceResponse # Import response models
from app.services.calculator import PortfolioPerformanceCalculator # Corrected import path
from datetime import date # Keep date for type hinting

 
router = APIRouter()

@router.post("/calculate_performance", response_model=PerformanceResponse)
async def calculate_performance_endpoint(request: PerformanceRequest):
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
        "metric_basis": request.metric_basis,
        "report_start_date": request.report_start_date.strftime("%Y-%m-%d") if request.report_start_date else None,
        "report_end_date": request.report_end_date.strftime("%Y-%m-%d"),
        "period_type": request.period_type
    }

    try:
        calculator = PortfolioPerformanceCalculator(config)
        # Pass the daily_data list directly to the calculator
        calculated_results = calculator.calculate_performance(
            [item.model_dump(by_alias=True, exclude_unset=True) for item in daily_data], config
        )

        summary_performance = {}
        # Ensure there are results to summarize, and that report_end_date is valid
        if calculated_results and request.report_end_date:
            # Find the first day within the report period
            first_day_in_report = next((day for day in calculated_results if date.fromisoformat(day["Perf. Date"]) >= (request.report_start_date if request.report_start_date else date.min)), None) # [cite: 10, 11]
            # Find the last day within the report period
            last_day_in_report = next((day for day in reversed(calculated_results) if date.fromisoformat(day["Perf. Date"]) <= request.report_end_date), None) # [cite: 11]

            if first_day_in_report and last_day_in_report:
                summary_performance["report_start_date"] = config.get("report_start_date") # [cite: 12]
                summary_performance["report_end_date"] = config.get("report_end_date") # [cite: 12]
                summary_performance["Begin Market Value"] = first_day_in_report.get("Begin Market Value", 0.0) # [cite: 12]
                summary_performance["End Market Value"] = last_day_in_report.get("End Market Value", 0.0) # [cite: 12]

                # Sum up cashflows and fees, and check flags for the entire calculated period
                total_bod_cf = 0.0 # [cite: 12, 13]
                total_eod_cf = 0.0 # [cite: 13]
                total_mgmt_fees = 0.0 # [cite: 13]

                # Flags that should be 1 if TRUE for any day in the period
                summary_nctrl1 = 0 # [cite: 13, 14]
                summary_nctrl2 = 0 # [cite: 14]
                summary_nctrl3 = 0 # [cite: 14]
                summary_nctrl4 = 0 # [cite: 14]
                summary_perf_reset = 0 # [cite: 14]
                summary_nip = 0 # [cite: 14]


                for day_data in calculated_results: # Iterate through all calculated_results [cite: 15]
                    current_date = date.fromisoformat(day_data["Perf. Date"]) # [cite: 15, 16]
                    # Only sum cashflows/fees and check flags for days within the report_start_date and report_end_date
                    if (request.report_start_date is None or current_date >= request.report_start_date) and \
                       current_date <= request.report_end_date: # [cite: 16, 17]
                        total_bod_cf += day_data.get("BOD Cashflow", 0.0) # [cite: 17]
                        total_eod_cf += day_data.get("Eod Cashflow", 0.0) # [cite: 17]
                        total_mgmt_fees += day_data.get("Mgmt fees", 0.0) # [cite: 17]

                        if day_data.get("NCTRL 1") == 1: # [cite: 18]
                            summary_nctrl1 = 1
                        if day_data.get("NCTRL 2") == 1: # [cite: 18, 19]
                            summary_nctrl2 = 1
                        if day_data.get("NCTRL 3") == 1: # [cite: 19]
                            summary_nctrl3 = 1
                        if day_data.get("NCTRL 4") == 1: # [cite: 19, 20]
                            summary_nctrl4 = 1
                        if day_data.get("Perf Reset") == 1: # [cite: 20, 21]
                            summary_perf_reset = 1
                        if day_data.get("NIP") == 1: # [cite: 21]
                            summary_nip = 1

                summary_performance["BOD Cashflow"] = total_bod_cf # [cite: 21]
                summary_performance["Eod Cashflow"] = total_eod_cf # [cite: 21, 22]
                summary_performance["Mgmt fees"] = total_mgmt_fees # [cite: 22]
                summary_performance["Final Cummulative ROR %"] = last_day_in_report.get("Final Cummulative ROR %", 0.0) # [cite: 22]

                summary_performance["NCTRL 1"] = summary_nctrl1 # [cite: 22]
                summary_performance["NCTRL 2"] = summary_nctrl2 # [cite: 22, 23]
                summary_performance["NCTRL 3"] = summary_nctrl3 # [cite: 23]
                summary_performance["NCTRL 4"] = summary_nctrl4 # [cite: 23]
                summary_performance["Perf Reset"] = summary_perf_reset # [cite: 23]
                summary_performance["NIP"] = summary_nip # [cite: 23]
            else: # If no data points fall within the report range
                summary_performance = { # [cite: 23]
                    "report_start_date": config.get("report_start_date"), # [cite: 24]
                    "report_end_date": config.get("report_end_date"), # [cite: 24]
                    "Begin Market Value": 0.0, # [cite: 24]
                    "BOD Cashflow": 0.0, # [cite: 24]
                    "Eod Cashflow": 0.0, # [cite: 25]
                    "Mgmt fees": 0.0, # [cite: 25]
                    "End Market Value": 0.0, # [cite: 25]
                    "Final Cummulative ROR %": 0.0, # [cite: 25]
                    "NCTRL 1": 0, # [cite: 25]
                    "NCTRL 2": 0, # [cite: 26]
                    "NCTRL 3": 0, # [cite: 26]
                    "NCTRL 4": 0, # [cite: 26]
                    "Perf Reset": 0, # [cite: 26]
                    "NIP": 0 # [cite: 27]
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during performance calculation: {str(e)}")

    # Prepare the response data, ensuring field names match Pydantic model aliases
    response_data = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date,
        "metric_basis": request.metric_basis,
        "period_type": request.period_type,
        "calculated_daily_performance": calculated_results, # [cite: 28]
        "summary_performance": summary_performance # [cite: 28]
    }

    return response_data