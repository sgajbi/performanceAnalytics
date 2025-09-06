# app/models/attribution_requests.py
from datetime import date
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from common.enums import (
    AttributionMode,
    AttributionModel,
    Frequency,
    LinkingMethod,
    PeriodType,
)
from core.envelope import Annualization, Calendar, Flags, Output, Periods
from app.models.requests import DailyInputData


class AttributionPortfolioData(BaseModel):
    """Contains the full time series and config for the total portfolio for attribution."""
    report_start_date: date
    report_end_date: date
    metric_basis: Literal["NET", "GROSS"]
    period_type: PeriodType
    daily_data: List[DailyInputData]


class InstrumentData(BaseModel):
    """Time series and metadata for a single instrument."""
    instrument_id: str
    meta: Dict[str, Any]
    daily_data: List[DailyInputData]


class BenchmarkGroup(BaseModel):
    """Time series data for a single benchmark group."""
    key: Dict[str, Any]
    observations: List[Dict]


class PortfolioGroup(BaseModel):
    """Pre-aggregated time series data for a single portfolio group."""
    key: Dict[str, Any]
    observations: List[Dict]


class AttributionRequest(BaseModel):
    """Request model for the Attribution engine."""
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    mode: AttributionMode
    frequency: Frequency = Frequency.MONTHLY
    group_by: List[str] = Field(..., min_length=1, alias="groupBy")
    model: AttributionModel = AttributionModel.BRINSON_FACHLER
    linking: LinkingMethod = LinkingMethod.CARINO

    # Mode-dependent fields
    portfolio_data: Optional[AttributionPortfolioData] = None
    instruments_data: Optional[List[InstrumentData]] = None
    portfolio_groups_data: Optional[List[PortfolioGroup]] = None

    # Benchmark is always by group
    benchmark_groups_data: List[BenchmarkGroup]

    # --- Shared Envelope Fields (Optional) ---
    as_of: Optional[date] = None
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    periods: Optional[Periods] = None
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)