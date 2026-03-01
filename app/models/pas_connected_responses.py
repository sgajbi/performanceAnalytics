from datetime import date
from typing import Literal

from pydantic import BaseModel


class PasConnectedPeriodResult(BaseModel):
    period: str
    start_date: date | None = None
    end_date: date | None = None
    net_cumulative_return: float | None = None
    net_annualized_return: float | None = None
    gross_cumulative_return: float | None = None
    gross_annualized_return: float | None = None


class PasConnectedTwrResponse(BaseModel):
    portfolio_id: str
    as_of_date: date
    source_mode: Literal["core_api_ref"] = "core_api_ref"
    source_service: str = "lotus-performance"
    pas_contract_version: str
    consumer_system: str | None = None
    results_by_period: dict[str, PasConnectedPeriodResult]


PasInputPeriodResult = PasConnectedPeriodResult
PasInputTwrResponse = PasConnectedTwrResponse
