from datetime import date

from pydantic import BaseModel, Field


class PasInputTwrRequest(BaseModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        description="Portfolio identifier in PAS.",
        examples=["DEMO_DPM_EUR_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for PAS core snapshot retrieval.",
        examples=["2026-02-24"],
    )
    periods: list[str] | None = Field(
        default=None,
        description="Optional list of period keys to keep (for example: YTD, MTD).",
        examples=[["YTD", "MTD"]],
    )
    consumer_system: str = Field(
        default="PA",
        alias="consumerSystem",
        description="Consumer system identifier forwarded to PAS integration contract.",
        examples=["BFF"],
    )
    lookback_days: int = Field(
        400,
        ge=30,
        le=2000,
        alias="lookbackDays",
        description="Maximum days of PAS raw valuation history requested for PA calculation.",
        examples=[400],
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "portfolioId": "DEMO_DPM_EUR_001",
                "asOfDate": "2026-02-24",
                "periods": ["YTD"],
                "consumerSystem": "BFF",
                "lookbackDays": 400,
            }
        },
    }
