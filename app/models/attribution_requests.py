# app/models/attribution_requests.py
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.enums import (
    AttributionMode,
    AttributionModel,
    Frequency,
    LinkingMethod,
    PeriodType,
)
from core.envelope import Annualization, Calendar, Flags, Output, FXRequestBlock, HedgingRequestBlock
from app.models.requests import DailyInputData


class AttributionPortfolioData(BaseModel):
    """Contains the full time series and config for the total portfolio for attribution."""
    metric_basis: Literal["NET", "GROSS"]
    daily_data: List[DailyInputData]


class InstrumentData(BaseModel):
    """Time series and metadata for a single instrument."""
    instrument_id: str
    meta: Dict[str, Any]
    daily_data: List[DailyInputData]


class BenchmarkObservation(BaseModel):
    """Represents a single benchmark data point for a period."""
    date: date
    weight_bop: float
    return_base: float
    return_local: Optional[float] = None
    return_fx: Optional[float] = None


class BenchmarkGroup(BaseModel):
    """Time series data for a single benchmark group."""
    key: Dict[str, Any]
    observations: List[BenchmarkObservation]


class PortfolioGroup(BaseModel):
    """Pre-aggregated time series data for a single portfolio group."""
    key: Dict[str, Any]
    observations: List[Dict]


class AttributionRequest(BaseModel):
    """Request model for the Attribution engine."""
    model_config = ConfigDict(extra="forbid")

    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    report_start_date: date
    report_end_date: date
    period_type: Optional[PeriodType] = None  # Deprecated in favor of 'periods'
    periods: Optional[List[PeriodType]] = None  # New field for multi-period requests

    mode: AttributionMode
    frequency: Frequency = Frequency.MONTHLY
    group_by: List[str] = Field(..., min_length=1)
    model: AttributionModel = AttributionModel.BRINSON_FACHLER
    linking: LinkingMethod = LinkingMethod.CARINO
    portfolio_data: Optional[AttributionPortfolioData] = None
    instruments_data: Optional[List[InstrumentData]] = None
    portfolio_groups_data: Optional[List[PortfolioGroup]] = None
    benchmark_groups_data: List[BenchmarkGroup]
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)
    currency_mode: Optional[Literal["BASE_ONLY", "LOCAL_ONLY", "BOTH"]] = "BASE_ONLY"
    report_ccy: Optional[str] = None
    fx: Optional[FXRequestBlock] = None
    hedging: Optional[HedgingRequestBlock] = None

    @model_validator(mode="before")
    @classmethod
    def check_period_definition(cls, values):
        """Ensures that exactly one period definition method is used."""
        has_periods = "periods" in values and values.get("periods") is not None
        has_period_type = "period_type" in values and values.get("period_type") is not None

        if not (has_periods ^ has_period_type):
            raise ValueError("Exactly one of 'periods' or 'period_type' must be provided.")

        if has_periods and not values["periods"]:
            raise ValueError("The 'periods' list cannot be empty.")

        return values