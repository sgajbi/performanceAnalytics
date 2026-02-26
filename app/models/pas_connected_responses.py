from datetime import date
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class PasConnectedPeriodResult(BaseModel):
    period: str
    start_date: date | None = None
    end_date: date | None = None
    net_cumulative_return: float | None = None
    net_annualized_return: float | None = None
    gross_cumulative_return: float | None = None
    gross_annualized_return: float | None = None


class PasConnectedTwrResponse(BaseModel):
    portfolio_id: str = Field(
        validation_alias=AliasChoices("portfolio_id", "portfolioId"),
        serialization_alias="portfolio_id",
    )
    as_of_date: date
    source_mode: Literal["pas_ref"] = "pas_ref"
    source_service: str = "lotus-performance"
    pas_contract_version: str = Field(..., alias="pasContractVersion")
    consumer_system: str | None = Field(default=None, alias="consumerSystem")
    results_by_period: dict[str, PasConnectedPeriodResult] = Field(alias="resultsByPeriod")

    model_config = {"populate_by_name": True}


PasInputPeriodResult = PasConnectedPeriodResult
PasInputTwrResponse = PasConnectedTwrResponse
