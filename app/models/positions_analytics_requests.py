from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PositionAnalyticsRequest(BaseModel):
    portfolio_id: str = Field(..., alias="portfolioId", examples=["DEMO_DPM_EUR_001"])
    as_of_date: date = Field(..., alias="asOfDate", examples=["2026-02-24"])
    sections: list[str] = Field(
        default_factory=lambda: ["BASE", "INSTRUMENT_DETAILS", "VALUATION", "INCOME", "PERFORMANCE"]
    )
    performance_periods: list[Literal["MTD", "QTD", "YTD", "ONE_YEAR", "SI"]] | None = Field(
        default=None,
        alias="performancePeriods",
    )
    consumer_system: str = Field("PA", alias="consumerSystem", examples=["BFF"])

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "portfolioId": "DEMO_DPM_EUR_001",
                "asOfDate": "2026-02-24",
                "sections": ["BASE", "INSTRUMENT_DETAILS", "VALUATION", "PERFORMANCE"],
                "performancePeriods": ["YTD", "MTD"],
                "consumerSystem": "BFF",
            }
        },
    }
