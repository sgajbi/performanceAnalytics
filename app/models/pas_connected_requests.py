from datetime import date

from pydantic import BaseModel, Field


class PasInputTwrRequest(BaseModel):
    portfolio_id: str = Field(
        ...,
        alias="portfolioId",
        description="Portfolio identifier in PAS.",
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for PAS core snapshot retrieval.",
    )
    periods: list[str] | None = Field(
        default=None,
        description="Optional list of period keys to keep (for example: YTD, MTD).",
    )
    consumer_system: str = Field(
        default="PA",
        alias="consumerSystem",
        description="Consumer system identifier forwarded to PAS integration contract.",
    )
    lookback_days: int = Field(
        400,
        ge=30,
        le=2000,
        alias="lookbackDays",
        description="Maximum days of PAS raw valuation history requested for PA calculation.",
    )

    model_config = {"populate_by_name": True}
