from datetime import date

from pydantic import BaseModel, Field


class PasConnectedTwrRequest(BaseModel):
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
    include_sections: list[str] = Field(
        default_factory=lambda: ["PERFORMANCE"],
        alias="includeSections",
        description="PAS snapshot sections requested; PERFORMANCE required for this endpoint.",
    )

    model_config = {"populate_by_name": True}
