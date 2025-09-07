# app/models/responses.py
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from common.enums import Frequency
from core.envelope import Audit, Diagnostics, Meta


class PerformanceSummary(BaseModel):
    """A summary of performance for a given period (day, month, etc.)."""
    model_config = ConfigDict(populate_by_name=True)

    begin_mv: float
    end_mv: float
    net_cash_flow: float
    period_return_pct: float
    cumulative_return_pct_to_date: Optional[float] = None
    annualized_return_pct: Optional[float] = None
    final_cum_ror: Optional[float] = None


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