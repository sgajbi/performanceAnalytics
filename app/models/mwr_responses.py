# app/models/mwr_responses.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from core.envelope import Audit, Diagnostics, Meta


class MoneyWeightedReturnResponse(BaseModel):
    """Response model for a Money-Weighted Return calculation."""
    calculation_id: UUID
    portfolio_number: str
    money_weighted_return: float

    # --- Shared Envelope Fields ---
    meta: Optional[Meta] = None
    diagnostics: Optional[Diagnostics] = None
    audit: Optional[Audit] = None