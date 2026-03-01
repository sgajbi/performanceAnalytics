from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PositionAnalyticsRequest(BaseModel):
    portfolio_id: str = Field(..., examples=["DEMO_DPM_EUR_001"])
    as_of_date: date = Field(..., examples=["2026-02-24"])
    sections: list[str] = Field(
        default_factory=lambda: ["BASE", "INSTRUMENT_DETAILS", "VALUATION", "INCOME", "PERFORMANCE"]
    )
    performance_periods: list[Literal["MTD", "QTD", "YTD", "ONE_YEAR", "SI"]] | None = Field(
        default=None,
    )
    consumer_system: str = Field("lotus-performance", examples=["lotus-gateway"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_id": "DEMO_DPM_EUR_001",
                "as_of_date": "2026-02-24",
                "sections": ["BASE", "INSTRUMENT_DETAILS", "VALUATION", "PERFORMANCE"],
                "performance_periods": ["YTD", "MTD"],
                "consumer_system": "lotus-gateway",
            }
        },
    }
