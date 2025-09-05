# app/models/mwr_responses.py
from uuid import UUID
from pydantic import BaseModel


class MoneyWeightedReturnResponse(BaseModel):
    """Response model for a Money-Weighted Return calculation."""
    calculation_id: UUID
    portfolio_number: str
    money_weighted_return: float