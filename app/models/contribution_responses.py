# app/models/contribution_responses.py
from datetime import date
from typing import List
from uuid import UUID

from pydantic import BaseModel


class PositionContribution(BaseModel):
    """Details the contribution of a single position."""
    position_id: str
    total_contribution: float
    average_weight: float
    total_return: float


class ContributionResponse(BaseModel):
    """Response model for the Contribution engine."""
    calculation_id: UUID
    portfolio_number: str
    report_start_date: date
    report_end_date: date
    total_portfolio_return: float
    total_contribution: float
    position_contributions: List[PositionContribution]