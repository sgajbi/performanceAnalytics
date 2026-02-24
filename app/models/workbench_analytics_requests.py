from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class WorkbenchPositionInput(BaseModel):
    security_id: str = Field(..., alias="securityId")
    instrument_name: str = Field(..., alias="instrumentName")
    asset_class: str | None = Field(default=None, alias="assetClass")
    quantity: float

    model_config = {"populate_by_name": True}


class WorkbenchProjectedPositionInput(BaseModel):
    security_id: str = Field(..., alias="securityId")
    instrument_name: str = Field(..., alias="instrumentName")
    asset_class: str | None = Field(default=None, alias="assetClass")
    baseline_quantity: float = Field(..., alias="baselineQuantity")
    proposed_quantity: float = Field(..., alias="proposedQuantity")
    delta_quantity: float = Field(..., alias="deltaQuantity")

    model_config = {"populate_by_name": True}


class WorkbenchAnalyticsRequest(BaseModel):
    portfolio_id: str = Field(..., alias="portfolioId")
    as_of_date: date = Field(..., alias="asOfDate")
    period: str = "YTD"
    group_by: Literal["ASSET_CLASS", "SECURITY"] = Field("ASSET_CLASS", alias="groupBy")
    benchmark_code: str = Field("MODEL_60_40", alias="benchmarkCode")
    portfolio_return_pct: float | None = Field(default=None, alias="portfolioReturnPct")
    benchmark_return_pct: float | None = Field(default=None, alias="benchmarkReturnPct")
    current_positions: list[WorkbenchPositionInput] = Field(default_factory=list, alias="currentPositions")
    projected_positions: list[WorkbenchProjectedPositionInput] = Field(default_factory=list, alias="projectedPositions")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "portfolioId": "DEMO_DPM_EUR_001",
                "asOfDate": "2026-02-24",
                "period": "YTD",
                "groupBy": "ASSET_CLASS",
                "benchmarkCode": "MODEL_60_40",
                "portfolioReturnPct": 4.2,
                "benchmarkReturnPct": 3.8,
                "currentPositions": [
                    {
                        "securityId": "AAPL.US",
                        "instrumentName": "Apple Inc",
                        "assetClass": "EQUITY",
                        "quantity": 120.0,
                    }
                ],
                "projectedPositions": [
                    {
                        "securityId": "AAPL.US",
                        "instrumentName": "Apple Inc",
                        "assetClass": "EQUITY",
                        "baselineQuantity": 120.0,
                        "proposedQuantity": 100.0,
                        "deltaQuantity": -20.0,
                    }
                ],
            }
        },
    }
