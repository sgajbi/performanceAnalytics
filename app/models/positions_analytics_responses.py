from datetime import date

from pydantic import BaseModel, Field


class PositionAnalyticsResponse(BaseModel):
    source_mode: str = "pas_ref"
    source_service: str = "lotus-performance"
    portfolio_id: str = Field(..., alias="portfolioId")
    as_of_date: date = Field(..., alias="asOfDate")
    total_market_value: float = Field(..., alias="totalMarketValue")
    positions: list[dict] = Field(
        ...,
        description="Position-level analytics rows normalized under lotus-performance contract.",
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "source_mode": "pas_ref",
                "source_service": "lotus-performance",
                "portfolioId": "DEMO_DPM_EUR_001",
                "asOfDate": "2026-02-24",
                "totalMarketValue": 1250000.0,
                "positions": [{"securityId": "EQ_1", "quantity": 100.0}],
            }
        },
    }
