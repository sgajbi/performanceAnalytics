# app/models/mwr_responses.py
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.mwr_requests import CashFlow
from core.envelope import Audit, Diagnostics, Meta


class Convergence(BaseModel):
    iterations: Optional[int] = None
    residual: Optional[float] = None
    converged: Optional[bool] = None


class MWRResult(BaseModel):
    """A simple data container for the results of an MWR calculation from the engine."""
    mwr: float
    mwr_annualized: Optional[float] = None
    method: Literal["XIRR", "MODIFIED_DIETZ", "DIETZ"]
    start_date: date
    end_date: date
    notes: List[str]
    convergence: Optional[Convergence] = None


class MoneyWeightedReturnResponse(BaseModel):
    """Response model for a Money-Weighted Return calculation."""
    calculation_id: UUID
    portfolio_number: str

    # --- RFC-016 Fields ---
    mwr: float = Field(alias="money_weighted_return")
    mwr_annualized: Optional[float] = None
    method: Literal["XIRR", "MODIFIED_DIETZ", "DIETZ"]
    convergence: Optional[Convergence] = None
    cashflows_used: Optional[List[CashFlow]] = None
    start_date: date
    end_date: date
    notes: List[str]

    # --- Shared Envelope Fields ---
    meta: Meta
    diagnostics: Diagnostics
    audit: Audit

    class Config:
        populate_by_name = True