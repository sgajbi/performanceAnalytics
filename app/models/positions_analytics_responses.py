from datetime import date

from pydantic import BaseModel, Field


class PositionAnalyticsResponse(BaseModel):
    source_mode: str = "pas_ref"
    source_service: str = "performance-analytics"
    portfolio_id: str = Field(..., alias="portfolioId")
    as_of_date: date = Field(..., alias="asOfDate")
    total_market_value: float = Field(..., alias="totalMarketValue")
    positions: list[dict]

    model_config = {"populate_by_name": True}
