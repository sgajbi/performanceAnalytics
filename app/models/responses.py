from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional

# Pydantic model for a single daily performance entry in the response
class DailyPerformance(BaseModel):
    Day: int
    perf_date: str = Field(..., alias="Perf. Date") # Alias for field with dot [cite: 3]
    begin_market_value: float = Field(..., alias="Begin Market Value") # [cite: 3]
    bod_cashflow: float = Field(..., alias="BOD Cashflow") # [cite: 3]
    eod_cashflow: float = Field(..., alias="Eod Cashflow") # [cite: 3]
    mgmt_fees: float = Field(..., alias="Mgmt fees") # [cite: 3]
    end_market_value: float = Field(..., alias="End Market Value") # [cite: 3]
    sign: float
    daily_ror_percent: float = Field(..., alias="daily ror %") # [cite: 3]
    temp_long_cum_ror_percent: float = Field(..., alias="Temp Long Cum Ror %") # [cite: 3]
    temp_short_cum_ror_percent: float = Field(..., alias="Temp short Cum RoR %") # [cite: 3]
    nctrl_1: int = Field(..., alias="NCTRL 1") # [cite: 4]
    nctrl_2: int = Field(..., alias="NCTRL 2") # [cite: 4]
    nctrl_3: int = Field(..., alias="NCTRL 3") # [cite: 4]
    nctrl_4: int = Field(..., alias="NCTRL 4") # [cite: 4]
    perf_reset: int = Field(..., alias="Perf Reset") # [cite: 4]
    nip: int = Field(..., alias="NIP") # NIP field was missing alias
    long_cum_ror_percent: float = Field(..., alias="Long Cum Ror %") # [cite: 4]
    short_cum_ror_percent: float = Field(..., alias="Short Cum RoR %") # [cite: 4]
    long_short: str = Field(..., alias="Long /Short") # [cite: 4]
    final_cummulative_ror_percent: float = Field(..., alias="Final Cummulative ROR %") # [cite: 4]


# Pydantic model for the summary performance object
class SummaryPerformance(BaseModel):
    report_start_date: Optional[date] = None # [cite: 5]
    report_end_date: date # Made mandatory [cite: 5]
    begin_market_value: float = Field(..., alias="Begin Market Value") # [cite: 5]
    bod_cashflow: float = Field(..., alias="BOD Cashflow") # [cite: 5]
    eod_cashflow: float = Field(..., alias="Eod Cashflow") # [cite: 5]
    mgmt_fees: float = Field(..., alias="Mgmt fees") # [cite: 5]
    end_market_value: float = Field(..., alias="End Market Value") # [cite: 5]
    final_cummulative_ror_percent: float = Field(..., alias="Final Cummulative ROR %") # [cite: 5]
    nctrl_1: int = Field(..., alias="NCTRL 1") # [cite: 5]
    nctrl_2: int = Field(..., alias="NCTRL 2") # [cite: 6]
    nctrl_3: int = Field(..., alias="NCTRL 3") # [cite: 6]
    nctrl_4: int = Field(..., alias="NCTRL 4") # [cite: 6]
    perf_reset: int = Field(..., alias="Perf Reset") # [cite: 6]
    nip: int = Field(..., alias="NIP") # [cite: 6]

# Pydantic model for the full API response
class PerformanceResponse(BaseModel):
    portfolio_number: str
    performance_start_date: date
    metric_basis: str
    period_type: str
    calculated_daily_performance: List[DailyPerformance]
    summary_performance: SummaryPerformance