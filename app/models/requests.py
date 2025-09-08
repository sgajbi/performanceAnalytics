# app/models/requests.py
from datetime import date
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from common.enums import Frequency, PeriodType
from core.envelope import Annualization, Calendar, Flags, Output, Periods, DataPolicy


class DailyInputData(BaseModel):
    day: int
    perf_date: date
    begin_mv: float
    bod_cf: float = 0.0
    eod_cf: float = 0.0
    mgmt_fees: float = 0.0
    end_mv: float


class FeeEffect(BaseModel):
    enabled: bool = False


class ResetPolicy(BaseModel):
    emit: bool = False


class PerformanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_id: UUID = Field(default_factory=uuid4)
    portfolio_number: str
    performance_start_date: date
    metric_basis: Literal["NET", "GROSS"]
    report_start_date: Optional[date] = None
    report_end_date: date
    period_type: PeriodType
    frequencies: List[Frequency] = [Frequency.DAILY]
    daily_data: List[DailyInputData]
    as_of: Optional[date] = None
    currency: str = "USD"
    precision_mode: Literal["FLOAT64", "DECIMAL_STRICT"] = "FLOAT64"
    rounding_precision: int = 6
    calendar: Calendar = Field(default_factory=Calendar)
    annualization: Annualization = Field(default_factory=Annualization)
    periods: Optional[Periods] = None
    output: Output = Field(default_factory=Output)
    flags: Flags = Field(default_factory=Flags)
    fee_effect: FeeEffect = Field(default_factory=FeeEffect)
    reset_policy: ResetPolicy = Field(default_factory=ResetPolicy)
    data_policy: Optional[DataPolicy] = None 