# app/models/requests.py
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    MGMT_FEES_FIELD,
    PERF_DATE_FIELD,
)
from common.enums import Frequency, PeriodType
from core.envelope import Annualization, Calendar, Flags, Output, Periods


class DailyInputData(BaseModel):
    Day: int
    perf_date: date = Field(..., alias=PERF_DATE_FIELD)
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)


class PerformanceRequest(BaseModel):
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    performance_start_date: date
    metric_basis: Literal["NET", "GROSS"]
    report_start_date: Optional[date] = None
    report_end_date: date
    period_type: PeriodType
    frequencies: List[Frequency] = [Frequency.DAILY]
    rounding_precision: int = 4
    daily_data: List[DailyInputData]

    # --- Shared Envelope Fields (Optional) ---
    as_of: Optional[date] = None
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    periods: Optional[Periods] = None
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)