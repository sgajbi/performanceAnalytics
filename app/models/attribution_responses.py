# app/models/attribution_responses.py
from typing import Dict, List, Any, Optional
from uuid import UUID
from pydantic import BaseModel, model_validator
from common.enums import AttributionModel, LinkingMethod
from core.envelope import Meta, Diagnostics, Audit


class AttributionGroupResult(BaseModel):
    """The calculated attribution effects for a single group."""
    key: Dict[str, Any]
    allocation: float
    selection: float
    interaction: float
    total_effect: float


class AttributionLevelTotals(BaseModel):
    """The summed attribution effects for an entire level."""
    allocation: float
    selection: float
    interaction: float
    total_effect: float


class AttributionLevelResult(BaseModel):
    """The complete set of results for a single dimension/level of the hierarchy."""
    dimension: str
    parent_key: Optional[Dict[str, Any]] = None
    groups: List[AttributionGroupResult]
    totals: AttributionLevelTotals


class Reconciliation(BaseModel):
    """Validation block to confirm the sum of effects matches the active return."""
    total_active_return: float
    sum_of_effects: float
    residual: float


class CurrencyAttributionEffects(BaseModel):
    """The four decomposed effects from the Karnosky-Singer model."""
    local_allocation: float
    local_selection: float
    currency_allocation: float
    currency_selection: float # Captures interaction
    total_effect: float


class CurrencyAttributionResult(BaseModel):
    """The complete currency attribution breakdown for a single currency."""
    currency: str
    weight_portfolio_avg: float
    weight_benchmark_avg: float
    effects: CurrencyAttributionEffects


class CurrencyAttributionTotals(BaseModel):
    """The summed currency attribution effects across all currencies."""
    effects: CurrencyAttributionEffects
    reconciliation_residual_bp: float


class SinglePeriodAttributionResult(BaseModel):
    """Contains the full set of attribution results for a single, resolved period."""
    levels: List[AttributionLevelResult]
    reconciliation: Reconciliation
    currency_attribution: Optional[List[CurrencyAttributionResult]] = None
    currency_attribution_totals: Optional[CurrencyAttributionTotals] = None


class AttributionResponse(BaseModel):
    """Response model for the Attribution engine."""
    calculation_id: UUID
    portfolio_number: str
    model: AttributionModel
    linking: LinkingMethod

    # New multi-period structure
    results_by_period: Optional[Dict[str, SinglePeriodAttributionResult]] = None

    # Legacy single-period fields
    levels: Optional[List[AttributionLevelResult]] = None
    reconciliation: Optional[Reconciliation] = None
    currency_attribution: Optional[List[CurrencyAttributionResult]] = None
    currency_attribution_totals: Optional[CurrencyAttributionTotals] = None

    meta: Optional[Meta] = None
    diagnostics: Optional[Diagnostics] = None
    audit: Optional[Audit] = None

    @model_validator(mode="before")
    @classmethod
    def check_result_structure(cls, values):
        """Ensures that exactly one result structure is used."""
        has_new_structure = "results_by_period" in values and values.get("results_by_period") is not None
        has_legacy_structure = "levels" in values and values.get("levels") is not None

        if not (has_new_structure ^ has_legacy_structure):
            raise ValueError("Provide either 'results_by_period' or legacy 'levels' field, but not both.")

        return values