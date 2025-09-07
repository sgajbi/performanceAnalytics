# app/models/responses.py
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator, ConfigDict

from app.core.constants import *
from common.enums import Frequency
from core.envelope import Audit, Diagnostics, Meta


class PerformanceSummary(BaseModel):
    """A summary of performance for a given period (day, month, etc.)."""
    model_config = ConfigDict(populate_by_name=True)

    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    net_cash_flow: float
    period_return_pct: float
    cumulative_return_pct_to_date: Optional[float] = None
    annualized_return_pct: Optional[float] = None

    final_cumulative_ror: Optional[float] = Field(default=None, alias=FINAL_CUMULATIVE_ROR_PERCENT_FIELD)

    @model_validator(mode="before")
    def rename_legacy_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if FINAL_CUMULATIVE_ROR_PERCENT_FIELD in values:
            values["period_return_pct"] = values.pop(FINAL_CUMULATIVE_ROR_PERCENT_FIELD)
        return values


class PerformanceResultItem(BaseModel):
    """Represents a single period's result within a breakdown."""
    period: str
    summary: PerformanceSummary
    daily_data: Optional[List[Dict]] = None


PerformanceBreakdown = Dict[Frequency, List[PerformanceResultItem]]


class ResetEvent(BaseModel):
    date: date
    reason: str
    impacted_rows: int


class PerformanceResponse(BaseModel):
    calculation_id: UUID
    portfolio_number: str
    breakdowns: PerformanceBreakdown
    reset_events: Optional[List[ResetEvent]] = None

    meta: Meta
    diagnostics: Diagnostics
    audit: Audit