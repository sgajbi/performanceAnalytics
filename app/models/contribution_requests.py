# app/models/contribution_requests.py
from datetime import date
from typing import Any, Dict, List, Literal, Optional
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
from common.enums import PeriodType, WeightingScheme
from core.envelope import Annualization, Calendar, Flags, Output, Periods


class PositionDailyData(BaseModel):
    """Time series data for a single position on a single day."""

    perf_date: date = Field(..., alias=PERF_DATE_FIELD)
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)
    Day: int 


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


class Smoothing(BaseModel):
    method: Literal["CARINO", "NONE"] = "CARINO"


class Emit(BaseModel):
    timeseries: bool = False
    by_position_timeseries: bool = False
    by_level: bool = False
    top_n_per_level: int = 20
    threshold_weight: float = 0.005
    include_other: bool = True
    include_unclassified: bool = True
    residual_per_position: bool = False


class Lookthrough(BaseModel):
    enabled: bool = False
    fallback_policy: Literal["error", "unclassified", "scale_to_1"] = "error"


class ContributionRequest(BaseModel):
    """Request model for the Contribution engine."""

    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    portfolio_data: PortfolioData
    positions_data: List[PositionData]

    hierarchy: Optional[List[str]] = None
    weighting_scheme: WeightingScheme = WeightingScheme.BOD
    smoothing: Smoothing = Field(default_factory=Smoothing)
    emit: Emit = Field(default_factory=Emit)
    lookthrough: Lookthrough = Field(default_factory=Lookthrough)
    bucketing: Optional[Dict[str, Any]] = None

    as_of: Optional[date] = None
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    periods: Optional[Periods] = None
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)