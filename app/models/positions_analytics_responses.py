from datetime import date

from pydantic import BaseModel, Field


class PositionAnalyticsResponse(BaseModel):
    source_mode: str = "core_api_ref"
    source_service: str = "lotus-performance"
    portfolio_id: str
    as_of_date: date
    total_market_value: float
    positions: list[dict] = Field(
        ...,
        description="Position-level analytics rows normalized under lotus-performance contract.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_mode": "core_api_ref",
                "source_service": "lotus-performance",
                "portfolio_id": "DEMO_DPM_EUR_001",
                "as_of_date": "2026-02-24",
                "total_market_value": 1250000.0,
                "positions": [{"securityId": "EQ_1", "quantity": 100.0}],
            }
        },
    }
