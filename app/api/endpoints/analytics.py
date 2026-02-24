from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.models.positions_analytics_requests import PositionAnalyticsRequest
from app.models.positions_analytics_responses import PositionAnalyticsResponse
from app.services.pas_snapshot_service import PasSnapshotService

router = APIRouter(tags=["Analytics"])
settings = get_settings()


@router.post(
    "/positions",
    response_model=PositionAnalyticsResponse,
    summary="Get position analytics via PA contract",
    description=(
        "Returns PA-owned position analytics contract. During migration, PA may source "
        "underlying position analytics payloads from PAS and normalize for consumers."
    ),
    responses={
        200: {"description": "Position analytics contract payload."},
        502: {"description": "Invalid upstream PAS payload shape for PA contract."},
    },
)
async def get_positions_analytics(request: PositionAnalyticsRequest):
    pas_service = PasSnapshotService(
        base_url=settings.PAS_QUERY_BASE_URL,
        timeout_seconds=settings.PAS_TIMEOUT_SECONDS,
    )
    status_code, payload = await pas_service.get_positions_analytics(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date,
        sections=request.sections,
        performance_periods=request.performance_periods,
    )
    if status_code >= status.HTTP_400_BAD_REQUEST:
        raise HTTPException(status_code=status_code, detail=str(payload))

    try:
        return PositionAnalyticsResponse(
            portfolioId=payload["portfolioId"],
            asOfDate=payload["asOfDate"],
            totalMarketValue=payload["totalMarketValue"],
            positions=payload.get("positions", []),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid PAS positions analytics payload: missing {exc}",
        ) from exc
