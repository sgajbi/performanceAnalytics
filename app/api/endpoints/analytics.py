from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.models.positions_analytics_requests import PositionAnalyticsRequest
from app.models.positions_analytics_responses import PositionAnalyticsResponse
from app.services.pas_input_service import PasInputService

router = APIRouter(tags=["Analytics"])
settings = get_settings()


def _pick(payload: dict[str, Any], snake_key: str, camel_key: str) -> Any:
    if snake_key in payload:
        return payload[snake_key]
    return payload[camel_key]


@router.post(
    "/positions",
    response_model=PositionAnalyticsResponse,
    summary="Get position analytics via lotus-performance contract",
    description=(
        "Returns lotus-performance-owned position analytics contract. During migration, lotus-performance may source "
        "underlying position analytics payloads from lotus-core and normalize for consumers."
    ),
    responses={
        200: {"description": "Position analytics contract payload."},
        502: {"description": "Invalid upstream lotus-core payload shape for lotus-performance contract."},
    },
)
async def get_positions_analytics(request: PositionAnalyticsRequest):
    pas_service = PasInputService(
        base_url=settings.PAS_QUERY_BASE_URL,
        timeout_seconds=settings.PAS_TIMEOUT_SECONDS,
        max_retries=settings.PAS_MAX_RETRIES,
        retry_backoff_seconds=settings.PAS_RETRY_BACKOFF_SECONDS,
    )
    status_code, payload = await pas_service.get_positions_analytics(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date,
        sections=request.sections,
        performance_periods=(
            [str(period) for period in request.performance_periods] if request.performance_periods is not None else None
        ),
    )
    if status_code >= status.HTTP_400_BAD_REQUEST:
        raise HTTPException(status_code=status_code, detail=str(payload))

    try:
        portfolio_id = _pick(payload, "portfolio_id", "portfolioId")
        as_of_date = _pick(payload, "as_of_date", "asOfDate")
        total_market_value = _pick(payload, "total_market_value", "totalMarketValue")
        return PositionAnalyticsResponse(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            total_market_value=total_market_value,
            positions=payload.get("positions", []),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid lotus-core positions analytics payload: missing {exc}",
        ) from exc
