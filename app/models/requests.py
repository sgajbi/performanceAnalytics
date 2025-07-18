from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    METRIC_BASIS_GROSS,
    METRIC_BASIS_NET,
    MGMT_FEES_FIELD,
    PERF_DATE_FIELD,
    PERIOD_TYPE_EXPLICIT,
    PERIOD_TYPE_MTD,
    PERIOD_TYPE_QTD,
    PERIOD_TYPE_YTD,
)


# Pydantic model for a single daily performance entry in the request (input data structure)
class DailyInputData(BaseModel):
    Day: int
    perf_date: date = Field(..., alias=PERF_DATE_FIELD)
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)


# Pydantic model for the API request body
class PerformanceRequest(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: Literal[METRIC_BASIS_NET, METRIC_BASIS_GROSS]
    report_start_date: Optional[date] = None
    report_end_date: date
    period_type: Literal[PERIOD_TYPE_MTD, PERIOD_TYPE_QTD, PERIOD_TYPE_YTD, PERIOD_TYPE_EXPLICIT] = Field(
        ..., alias="period_type"
    )  # Use alias for field name
    daily_data: List[DailyInputData]
