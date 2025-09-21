# app/models/responses.py
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator

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


class PortfolioReturnDecomposition(BaseModel):
    local: float
    fx: float
    base: float


class SinglePeriodPerformanceResult(BaseModel):
    """Contains the full set of TWR results for a single, resolved period."""

    breakdowns: PerformanceBreakdown
    reset_events: Optional[List[ResetEvent]] = None
    portfolio_return: Optional[PortfolioReturnDecomposition] = None


class PerformanceResponse(BaseModel):
    """
    The main response model for a TWR calculation.
    Can return results for multiple periods in 'results_by_period' or a single
    period's results in the legacy flat structure for backward compatibility.
    """

    calculation_id: UUID
    portfolio_number: str

    results_by_period: Optional[Dict[str, SinglePeriodPerformanceResult]] = None

    breakdowns: Optional[PerformanceBreakdown] = None
    reset_events: Optional[List[ResetEvent]] = None
    portfolio_return: Optional[PortfolioReturnDecomposition] = None

    meta: Meta
    diagnostics: Diagnostics
    audit: Audit

    @model_validator(mode="before")
    @classmethod
    def check_result_structure(cls, values):
        """Ensures that exactly one result structure is used."""
        has_new_structure = "results_by_period" in values and values.get("results_by_period") is not None
        has_legacy_structure = "breakdowns" in values and values.get("breakdowns") is not None

        if not (has_new_structure ^ has_legacy_structure):
            raise ValueError(
                "Provide either 'results_by_period' or the legacy 'breakdowns' field, but not both."
            )
        return values
