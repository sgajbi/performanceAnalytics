from datetime import date

from pydantic import BaseModel, Field


class PasInputTwrRequest(BaseModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        description="Portfolio identifier in lotus-core.",
        examples=["DEMO_DPM_EUR_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for lotus-core core snapshot retrieval.",
        examples=["2026-02-24"],
    )
    periods: list[str] | None = Field(
        default=None,
        description="Optional list of period keys to keep (for example: YTD, MTD).",
        examples=[["YTD", "MTD"]],
    )
    consumer_system: str = Field(
        default="lotus-performance",
        alias="consumerSystem",
        description="Consumer system identifier forwarded to lotus-core integration contract.",
        examples=["lotus-gateway"],
    )
    lookback_days: int = Field(
        400,
        ge=30,
        le=2000,
        alias="lookbackDays",
        description="Maximum days of lotus-core raw valuation history requested for lotus-performance calculation.",
        examples=[400],
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "portfolioId": "DEMO_DPM_EUR_001",
                "asOfDate": "2026-02-24",
                "periods": ["YTD"],
                "consumerSystem": "lotus-gateway",
                "lookbackDays": 400,
            }
        },
    }
