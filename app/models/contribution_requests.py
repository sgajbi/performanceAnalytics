# app/models/contribution_requests.py
from datetime import date
from typing import List, Literal

from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    MGMT_FEES_FIELD,
    PERF_DATE_FIELD,
)
from common.enums import PeriodType


class PositionDailyData(BaseModel):
    """Time series data for a single position on a single day."""
    perf_date: date = Field(..., alias=PERF_DATE_FIELD)
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)


class PositionData(BaseModel):
    """Contains the full time series for a single position."""
    position_id: str
    daily_data: List[PositionDailyData]


class PortfolioData(BaseModel):
    """Contains the full time series and config for the total portfolio."""
    report_start_date: date
    report_end_date: date
    metric_basis: Literal["NET", "GROSS"]
    period_type: PeriodType
    daily_data: List[PositionDailyData]


class ContributionRequest(BaseModel):
    """Request model for the Contribution engine."""
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    portfolio_data: PortfolioData
    positions_data: List[PositionData]