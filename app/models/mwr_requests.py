# app/models/mwr_requests.py
from datetime import date
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CashFlow(BaseModel):
    """Represents a single cash flow with its date and amount."""
    amount: float
    date: date


class MoneyWeightedReturnRequest(BaseModel):
    """Request model for calculating Money-Weighted Return."""
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    beginning_mv: float
    ending_mv: float
    cash_flows: List[CashFlow]