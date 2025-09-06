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


class Solver(BaseModel):
    method: str = "brent"
    max_iter: int = 200
    tolerance: float = 1e-10


class MoneyWeightedReturnRequest(BaseModel):
    """Request model for calculating Money-Weighted Return."""
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    beginning_mv: float
    ending_mv: float
    cash_flows: List[CashFlow]

    # --- RFC-016 Enhancements ---
    mwr_method: Literal["XIRR", "MODIFIED_DIETZ", "DIETZ"] = "XIRR"
    solver: Solver = Field(default_factory=Solver)
    emit_cashflows_used: bool = True

    # --- RFC-014 Shared Envelope Fields (Optional) ---
    as_of: date
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    periods: Optional[Periods] = None
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)