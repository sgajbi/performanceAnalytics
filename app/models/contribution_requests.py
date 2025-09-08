# app/models/contribution_requests.py
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from common.enums import PeriodType, WeightingScheme
from core.envelope import Annualization, Calendar, Flags, Output, Periods, DataPolicy


class PositionDailyData(BaseModel):
    """Time series data for a single position on a single day."""
    day: int
    perf_date: date
    begin_mv: float
    end_mv: float
    bod_cf: float = 0.0
    eod_cf: float = 0.0
    mgmt_fees: float = 0.0


class PositionData(BaseModel):
    """Contains the full time series and metadata for a single position."""

    position_id: str
    meta: Dict[str, Any] = Field(default_factory=dict)
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
    model_config = ConfigDict(extra="forbid")

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
    data_policy: Optional[DataPolicy] = None