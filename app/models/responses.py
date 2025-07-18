
from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional
from app.core.constants import ( #
    PERF_DATE_FIELD, BEGIN_MARKET_VALUE_FIELD, BOD_CASHFLOW_FIELD,
    EOD_CASHFLOW_FIELD, MGMT_FEES_FIELD, END_MARKET_VALUE_FIELD,
    DAILY_ROR_PERCENT_FIELD, TEMP_LONG_CUM_ROR_PERCENT_FIELD,
    TEMP_SHORT_CUM_ROR_PERCENT_FIELD, NCTRL_1_FIELD, NCTRL_2_FIELD,
    NCTRL_3_FIELD, NCTRL_4_FIELD, PERF_RESET_FIELD, NIP_FIELD,
    LONG_CUM_ROR_PERCENT_FIELD, SHORT_CUM_ROR_PERCENT_FIELD,
    LONG_SHORT_FIELD, FINAL_CUMULATIVE_ROR_PERCENT_FIELD
)

# Pydantic model for a single daily performance entry in the response
class DailyPerformance(BaseModel):
    Day: int
    perf_date: str = Field(..., alias=PERF_DATE_FIELD)
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    sign: float
    daily_ror_percent: float = Field(..., alias=DAILY_ROR_PERCENT_FIELD)
    temp_long_cum_ror_percent: float = Field(..., alias=TEMP_LONG_CUM_ROR_PERCENT_FIELD)
    temp_short_cum_ror_percent: float = Field(..., alias=TEMP_SHORT_CUM_ROR_PERCENT_FIELD)
    nctrl_1: int = Field(..., alias=NCTRL_1_FIELD)
    nctrl_2: int = Field(..., alias=NCTRL_2_FIELD)
    nctrl_3: int = Field(..., alias=NCTRL_3_FIELD)
    nctrl_4: int = Field(..., alias=NCTRL_4_FIELD)
    perf_reset: int = Field(..., alias=PERF_RESET_FIELD)
    nip: int = Field(..., alias=NIP_FIELD)
    long_cum_ror_percent: float = Field(..., alias=LONG_CUM_ROR_PERCENT_FIELD)
    short_cum_ror_percent: float = Field(..., alias=SHORT_CUM_ROR_PERCENT_FIELD)
    long_short: str = Field(..., alias=LONG_SHORT_FIELD)
    final_cumulative_ror_percent: float = Field(..., alias=FINAL_CUMULATIVE_ROR_PERCENT_FIELD)


# Pydantic model for the summary performance object
class SummaryPerformance(BaseModel):
    report_start_date: Optional[date] = None #
    report_end_date: date # Made mandatory
    begin_market_value: float = Field(..., alias=BEGIN_MARKET_VALUE_FIELD)
    bod_cashflow: float = Field(..., alias=BOD_CASHFLOW_FIELD)
    eod_cashflow: float = Field(..., alias=EOD_CASHFLOW_FIELD)
    mgmt_fees: float = Field(..., alias=MGMT_FEES_FIELD)
    end_market_value: float = Field(..., alias=END_MARKET_VALUE_FIELD)
    final_cumulative_ror_percent: float = Field(..., alias=FINAL_CUMULATIVE_ROR_PERCENT_FIELD)
    nctrl_1: int = Field(..., alias=NCTRL_1_FIELD)
    nctrl_2: int = Field(..., alias=NCTRL_2_FIELD)
    nctrl_3: int = Field(..., alias=NCTRL_3_FIELD)
    nctrl_4: int = Field(..., alias=NCTRL_4_FIELD)
    perf_reset: int = Field(..., alias=PERF_RESET_FIELD)
    nip: int = Field(..., alias=NIP_FIELD)

# Pydantic model for the full API response
class PerformanceResponse(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: str
    period_type: str
    calculated_daily_performance: List[DailyPerformance]
    summary_performance: SummaryPerformance