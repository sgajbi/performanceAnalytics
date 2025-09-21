# app/models/requests.py
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from common.enums import Frequency, PeriodType
from core.envelope import (
    Annualization,
    Calendar,
    DataPolicy,
    FXRequestBlock,
    Flags,
    HedgingRequestBlock,
    Output,
    Periods,
)


class DailyInputData(BaseModel):
    day: int = Field(..., description="A sequential day number for the record within the request payload.")
    perf_date: date = Field(..., description="The specific date of the observation in YYYY-MM-DD format.")
    begin_mv: float = Field(..., description="The market value of the portfolio at the beginning of the day, before any cash flows.")
    bod_cf: float = Field(0.0, description="Cash flow occurring at the beginning of the day (before trading). Positive for inflows, negative for outflows.")
    eod_cf: float = Field(0.0, description="Cash flow occurring at the end of the day (after trading). Positive for inflows, negative for outflows.")
    mgmt_fees: float = Field(0.0, description="Management or other fees charged for the day. Should be a negative value to reduce performance.")
    end_mv: float = Field(..., description="The market value of the portfolio at the end of the day.")


class FeeEffect(BaseModel):
    enabled: bool = False


class ResetPolicy(BaseModel):
    emit: bool = Field(False, description="If true, the response will include a list of any performance reset events that occurred.")


class Analysis(BaseModel):
    """Defines a single analysis with its period and desired frequencies."""
    period: PeriodType
    frequencies: List[Frequency]

    @field_validator('frequencies')
    @classmethod
    def frequencies_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('frequencies list cannot be empty for an analysis')
        return v


class PerformanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: UUID = Field(default_factory=uuid4, description="A unique identifier for the calculation request. If not provided, one will be generated.")
    portfolio_number: str = Field(..., description="A unique identifier for the portfolio being analyzed.")
    performance_start_date: date = Field(..., description="The inception date of the portfolio or the earliest date for which performance data is available.")
    metric_basis: Literal["NET", "GROSS"] = Field(..., description="Specifies whether to calculate returns 'NET' (after fees) or 'GROSS' (before fees).")
    report_start_date: Optional[date] = Field(None, description="The explicit start date for an 'EXPLICIT' period calculation. Ignored for other period types.")
    report_end_date: date = Field(..., description="The final date of the analysis period. Also used as the anchor date for resolving relative periods like YTD.")
    
    # --- START REFACTOR: Decouple periods and frequencies ---
    analyses: List[Analysis]
    # --- END REFACTOR ---

    valuation_points: List[DailyInputData]
    currency: str = Field("USD", description="The three-letter ISO currency code for the request (e.g., 'USD').")
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = Field("FLOAT64", description="The numerical precision mode for the calculation engine.")
    rounding_precision: int = Field(6, description="The number of decimal places to round final float results to.")
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)
    fee_effect: FeeEffect = Field(default_factory=FeeEffect)
    reset_policy: ResetPolicy = Field(default_factory=ResetPolicy)
    data_policy: Optional[DataPolicy] = None

    currency_mode: Optional[Literal["BASE_ONLY", "LOCAL_ONLY", "BOTH"]] = None
    report_ccy: Optional[str] = None
    fx: Optional[FXRequestBlock] = None
    hedging: Optional[HedgingRequestBlock] = None

    @field_validator('analyses')
    @classmethod
    def analyses_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('analyses list cannot be empty')
        return v