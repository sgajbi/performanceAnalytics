# app/models/responses.py
from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.constants import *
from common.enums import Frequency
from core.envelope import Audit, Diagnostics, Meta


class PerformanceSummary(BaseModel):
    """A summary of performance for a given period (day, month, etc.)."""
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    net_cash_flow: float
    final_cumulative_ror: float = Field(..., alias=FINAL_CUMULATIVE_ROR_PERCENT_FIELD)


class PerformanceResultItem(BaseModel):
    """Represents a single period's result within a breakdown."""
    period: str
    summary: PerformanceSummary
    # The full daily data will only be present for the "daily" frequency breakdown
    daily_data: Optional[List[Dict]] = None


PerformanceBreakdown = Dict[Frequency, List[PerformanceResultItem]]


class PerformanceResponse(BaseModel):
    calculation_id: UUID
    portfolio_number: str
    breakdowns: PerformanceBreakdown

    # --- Shared Envelope Fields (Now Mandatory) ---
    meta: Meta
    diagnostics: Diagnostics
    audit: Audit