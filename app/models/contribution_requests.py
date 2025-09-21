# app/models/contribution_requests.py
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.enums import PeriodType, WeightingScheme
from core.envelope import (
    Annualization,
    Calendar,
    DataPolicy,
    FXRequestBlock,
    Flags,
    HedgingRequestBlock,
    Output,
    Periods,
)


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

    metric_basis: Literal["NET", "GROSS"]
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
    report_start_date: date
    report_end_date: date
    period_type: Optional[PeriodType] = None  # Deprecated in favor of 'periods'
    periods: Optional[List[PeriodType]] = None  # New field for multi-period requests

    portfolio_data: PortfolioData
    positions_data: List[PositionData]
    hierarchy: Optional[List[str]] = None
    weighting_scheme: WeightingScheme = WeightingScheme.BOD
    smoothing: Smoothing = Field(default_factory=Smoothing)
    emit: Emit = Field(default_factory=Emit)
    lookthrough: Lookthrough = Field(default_factory=Lookthrough)
    bucketing: Optional[Dict[str, Any]] = None
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)
    data_policy: Optional[DataPolicy] = None

    currency_mode: Optional[Literal["BASE_ONLY", "LOCAL_ONLY", "BOTH"]] = None
    report_ccy: Optional[str] = None
    fx: Optional[FXRequestBlock] = None
    hedging: Optional[HedgingRequestBlock] = None

    @model_validator(mode="before")
    @classmethod
    def check_period_definition(cls, values):
        """Ensures that exactly one period definition method is used."""
        has_periods = "periods" in values and values["periods"] is not None
        has_period_type = "period_type" in values and values["period_type"] is not None

        if not (has_periods ^ has_period_type):
            raise ValueError("Exactly one of 'periods' or 'period_type' must be provided.")

        if has_periods and not values["periods"]:
            raise ValueError("The 'periods' list cannot be empty.")

        return values