# app/models/contribution_responses.py
from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from core.envelope import Audit, Diagnostics, Meta


class PositionContribution(BaseModel):
    """Details the contribution of a single position."""
    position_id: str
    total_contribution: float
    average_weight: float
    total_return: float


class DailyContribution(BaseModel):
    """Represents the total contribution for a single day."""
    date: date
    total_contribution: float


class PositionDailyContribution(BaseModel):
    """Represents a single day's contribution for a position."""
    date: date
    contribution: float


class PositionContributionSeries(BaseModel):
    """Contains the full contribution time series for a single position."""
    position_id: str
    series: List[PositionDailyContribution]


class ContributionResponse(BaseModel):
    """Response model for the Contribution engine."""
    calculation_id: UUID
    portfolio_number: str
    report_start_date: date
    report_end_date: date
    total_portfolio_return: float
    total_contribution: float
    position_contributions: List[PositionContribution]

    timeseries: Optional[List[DailyContribution]] = None
    by_position_timeseries: Optional[List[PositionContributionSeries]] = None

    meta: Meta
    diagnostics: Diagnostics
    audit: Audit