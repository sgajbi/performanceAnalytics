# app/models/attribution_requests.py
from typing import Dict, List, Literal, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from common.enums import AttributionMode, AttributionModel, LinkingMethod, Frequency
from app.models.contribution_requests import PortfolioData
from app.models.requests import DailyInputData


class InstrumentData(BaseModel):
    """Time series and metadata for a single instrument."""
    instrument_id: str
    meta: Dict[str, Any]
    daily_data: List[DailyInputData]


class BenchmarkGroup(BaseModel):
    """Time series data for a single benchmark group."""
    key: Dict[str, Any]
    observations: List[Dict] # e.g., {"date": "YYYY-MM-DD", "return": 0.05, "weight_bop": 0.10}


class PortfolioGroup(BaseModel):
    """Pre-aggregated time series data for a single portfolio group."""
    key: Dict[str, Any]
    observations: List[Dict] # e.g., {"date": "YYYY-MM-DD", "return": 0.05, "weight_bop": 0.10}


class AttributionRequest(BaseModel):
    """Request model for the Attribution engine."""
    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    mode: AttributionMode
    frequency: Frequency = Frequency.MONTHLY
    group_by: List[str] = Field(..., min_length=1)
    model: AttributionModel = AttributionModel.BRINSON_FACHLER
    linking: LinkingMethod = LinkingMethod.CARINO

    # Mode-dependent fields
    portfolio_data: Optional[PortfolioData] = None
    instruments_data: Optional[List[InstrumentData]] = None
    portfolio_groups_data: Optional[List[PortfolioGroup]] = None

    # Benchmark is always by group
    benchmark_groups_data: List[BenchmarkGroup]