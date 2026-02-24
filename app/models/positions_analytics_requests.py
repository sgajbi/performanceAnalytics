from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PositionAnalyticsRequest(BaseModel):
    portfolio_id: str = Field(..., alias="portfolioId")
    as_of_date: date = Field(..., alias="asOfDate")
    sections: list[str] = Field(
        default_factory=lambda: ["BASE", "INSTRUMENT_DETAILS", "VALUATION", "INCOME", "PERFORMANCE"]
    )
    performance_periods: list[Literal["MTD", "QTD", "YTD", "ONE_YEAR", "SI"]] | None = Field(
        default=None,
        alias="performancePeriods",
    )
    consumer_system: str = Field("PA", alias="consumerSystem")

    model_config = {"populate_by_name": True}
