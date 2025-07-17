from pydantic import BaseModel, Field
from datetime import date
from typing import List, Literal, Optional

# Pydantic model for a single daily performance entry in the request (input data structure)
class DailyInputData(BaseModel):
    Day: int
    perf_date: date = Field(..., alias="Perf. Date") # Alias for field with dot [cite: 2, 3]
    begin_market_value: float = Field(..., alias="Begin Market Value") # [cite: 3]
    bod_cashflow: float = Field(..., alias="BOD Cashflow") # [cite: 3]
    eod_cashflow: float = Field(..., alias="Eod Cashflow") # [cite: 3]
    mgmt_fees: float = Field(..., alias="Mgmt fees") # [cite: 3]
    end_market_value: float = Field(..., alias="End Market Value") # [cite: 3]

# Pydantic model for the API request body
class PerformanceRequest(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: Literal["NET", "GROSS"]
    report_start_date: Optional[date] = None
    report_end_date: date # Made mandatory [cite: 2]
    period_type: Literal["MTD", "QTD", "YTD", "Explicit"] = Field(..., alias="period_type") # Use alias for field name [cite: 2]
    daily_data: List[DailyInputData] # Added daily_data to the request payload