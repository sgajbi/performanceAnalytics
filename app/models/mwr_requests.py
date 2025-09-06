# app/models/mwr_requests.py
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from core.envelope import Annualization, Calendar, Flags, Output, Periods


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