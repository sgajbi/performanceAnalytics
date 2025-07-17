from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import date
from typing import List, Literal, Optional
import json
from pathlib import Path
from calculator import PortfolioPerformanceCalculator # Assuming calculator.py is in the same directory

app = FastAPI()

# Pydantic model for the API request body
class PerformanceRequest(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: Literal["NET", "GROSS"]
    report_start_date: Optional[date] = None
    report_end_date: date # Made mandatory
    period_type: Literal["MTD", "QTD", "YTD", "Explicit"] = Field(..., alias="period_type") # Use alias for field name

# Pydantic model for a single daily performance entry in the response
class DailyPerformance(BaseModel):
    Day: int
    Perf_Date: str = Field(..., alias="Perf. Date") # Alias for field with dot
    Begin_Market_Value: float = Field(..., alias="Begin Market Value")
    BOD_Cashflow: float = Field(..., alias="BOD Cashflow")
    Eod_Cashflow: float = Field(..., alias="Eod Cashflow")
    Mgmt_fees: float = Field(..., alias="Mgmt fees")
    End_Market_Value: float = Field(..., alias="End Market Value")
    sign: float
    daily_ror_percent: float = Field(..., alias="daily ror %")
    Temp_Long_Cum_Ror_percent: float = Field(..., alias="Temp Long Cum Ror %")
    Temp_short_Cum_RoR_percent: float = Field(..., alias="Temp short Cum RoR %")
    NCTRL_1: int = Field(..., alias="NCTRL 1")
    NCTRL_2: int = Field(..., alias="NCTRL 2")
    NCTRL_3: int = Field(..., alias="NCTRL 3")
    NCTRL_4: int = Field(..., alias="NCTRL 4")
    Perf_Reset: int = Field(..., alias="Perf Reset")
    NIP: int
    Long_Cum_Ror_percent: float = Field(..., alias="Long Cum Ror %")
    Short_Cum_RoR_percent: float = Field(..., alias="Short Cum RoR %")
    Long_Short: str = Field(..., alias="Long /Short")
    Final_Cummulative_ROR_percent: float = Field(..., alias="Final Cummulative ROR %")


# Pydantic model for the summary performance object
class SummaryPerformance(BaseModel):
    report_start_date: Optional[date] = None
    report_end_date: date # Made mandatory
    Begin_Market_Value: float = Field(..., alias="Begin Market Value")
    BOD_Cashflow: float = Field(..., alias="BOD Cashflow")
    Eod_Cashflow: float = Field(..., alias="Eod Cashflow")
    Mgmt_fees: float = Field(..., alias="Mgmt fees")
    End_Market_Value: float = Field(..., alias="End Market Value")
    Final_Cummulative_ROR_percent: float = Field(..., alias="Final Cummulative ROR %")
    NCTRL_1: int = Field(..., alias="NCTRL 1")
    NCTRL_2: int = Field(..., alias="NCTRL 2")
    NCTRL_3: int = Field(..., alias="NCTRL 3")
    NCTRL_4: int = Field(..., alias="NCTRL 4")
    Perf_Reset: int = Field(..., alias="Perf Reset")
    NIP: int

# Pydantic model for the full API response
class PerformanceResponse(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: str
    period_type: str
    calculated_daily_performance: List[DailyPerformance]
    summary_performance: SummaryPerformance


@app.post("/calculate_performance", response_model=PerformanceResponse)
async def calculate_performance_endpoint(request: PerformanceRequest):
    """
    Calculates portfolio performance based on the provided inputs and daily time series data.
    """
    input_file_path = Path(__file__).parent / "input.json"

    try:
        with open(input_file_path, 'r') as f:
            data = json.load(f)
            daily_data = data.get("daily_data")
            if not daily_data:
                raise HTTPException(status_code=400, detail="daily_data not found in input.json")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Input data file not found at {input_file_path}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Invalid JSON format in {input_file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading daily data: {str(e)}")

    # Prepare config for the calculator from the request
    config = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date.strftime("%Y-%m-%d"),
        "metric_basis": request.metric_basis,
        "report_start_date": request.report_start_date.strftime("%Y-%m-%d") if request.report_start_date else None,
        "report_end_date": request.report_end_date.strftime("%Y-%m-%d"), # Now mandatory
        "period_type": request.period_type
    }

    try:
        calculator = PortfolioPerformanceCalculator(config)
        calculated_results = calculator.calculate_performance(daily_data, config)

        summary_performance = {}
        # Ensure there are results to summarize, and that report_end_date is valid
        if calculated_results and request.report_end_date: 
            # Find the first day within the report period
            first_day_in_report = next((day for day in calculated_results if date.fromisoformat(day["Perf. Date"]) >= (request.report_start_date if request.report_start_date else date.min)), None)
            # Find the last day within the report period
            last_day_in_report = next((day for day in reversed(calculated_results) if date.fromisoformat(day["Perf. Date"]) <= request.report_end_date), None)


            if first_day_in_report and last_day_in_report:
                summary_performance["report_start_date"] = config.get("report_start_date")
                summary_performance["report_end_date"] = config.get("report_end_date")
                summary_performance["Begin Market Value"] = first_day_in_report.get("Begin Market Value", 0.0)
                summary_performance["End Market Value"] = last_day_in_report.get("End Market Value", 0.0)

                # Sum up cashflows and fees, and check flags for the entire calculated period
                total_bod_cf = 0.0
                total_eod_cf = 0.0
                total_mgmt_fees = 0.0
                
                # Flags that should be 1 if TRUE for any day in the period
                summary_nctrl1 = 0
                summary_nctrl2 = 0
                summary_nctrl3 = 0
                summary_nctrl4 = 0
                summary_perf_reset = 0
                summary_nip = 0

                for day_data in calculated_results: # Iterate through all calculated_results
                    current_date = date.fromisoformat(day_data["Perf. Date"])
                    # Only sum cashflows/fees and check flags for days within the report_start_date and report_end_date
                    if (request.report_start_date is None or current_date >= request.report_start_date) and \
                       current_date <= request.report_end_date:
                        total_bod_cf += day_data.get("BOD Cashflow", 0.0)
                        total_eod_cf += day_data.get("Eod Cashflow", 0.0)
                        total_mgmt_fees += day_data.get("Mgmt fees", 0.0)
                        
                        if day_data.get("NCTRL 1") == 1:
                            summary_nctrl1 = 1
                        if day_data.get("NCTRL 2") == 1:
                            summary_nctrl2 = 1
                        if day_data.get("NCTRL 3") == 1:
                            summary_nctrl3 = 1
                        if day_data.get("NCTRL 4") == 1:
                            summary_nctrl4 = 1
                        if day_data.get("Perf Reset") == 1:
                            summary_perf_reset = 1
                        if day_data.get("NIP") == 1:
                            summary_nip = 1

                summary_performance["BOD Cashflow"] = total_bod_cf
                summary_performance["Eod Cashflow"] = total_eod_cf
                summary_performance["Mgmt fees"] = total_mgmt_fees
                summary_performance["Final Cummulative ROR %"] = last_day_in_report.get("Final Cummulative ROR %", 0.0)
                
                summary_performance["NCTRL 1"] = summary_nctrl1
                summary_performance["NCTRL 2"] = summary_nctrl2
                summary_performance["NCTRL 3"] = summary_nctrl3
                summary_performance["NCTRL 4"] = summary_nctrl4
                summary_performance["Perf Reset"] = summary_perf_reset
                summary_performance["NIP"] = summary_nip
            else: # If no data points fall within the report range
                summary_performance = {
                    "report_start_date": config.get("report_start_date"),
                    "report_end_date": config.get("report_end_date"),
                    "Begin Market Value": 0.0,
                    "BOD Cashflow": 0.0,
                    "Eod Cashflow": 0.0,
                    "Mgmt fees": 0.0,
                    "End Market Value": 0.0,
                    "Final Cummulative ROR %": 0.0,
                    "NCTRL 1": 0,
                    "NCTRL 2": 0,
                    "NCTRL 3": 0,
                    "NCTRL 4": 0,
                    "Perf Reset": 0,
                    "NIP": 0
                }


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during performance calculation: {str(e)}")

    # Prepare the response data, ensuring field names match Pydantic model aliases
    response_data = {
        "portfolio_number": request.portfolio_number,
        "performance_start_date": request.performance_start_date,
        "metric_basis": request.metric_basis,
        "period_type": request.period_type,
        "calculated_daily_performance": calculated_results,
        "summary_performance": summary_performance
    }

    return response_data