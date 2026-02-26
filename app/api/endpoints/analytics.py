from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.models.positions_analytics_requests import PositionAnalyticsRequest
from app.models.positions_analytics_responses import PositionAnalyticsResponse
from app.models.workbench_analytics_requests import (
    WorkbenchAnalyticsRequest,
    WorkbenchProjectedPositionInput,
)
from app.models.workbench_analytics_responses import (
    WorkbenchAnalyticsBucket,
    WorkbenchAnalyticsResponse,
    WorkbenchTopChange,
)
from app.services.pas_input_service import PasInputService

router = APIRouter(tags=["Analytics"])
settings = get_settings()
_BENCHMARK_FALLBACK_RETURNS = {"MODEL_60_40": 3.1, "MSCI_ACWI": 4.2, "CUSTOM": 2.8}


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
        return PositionAnalyticsResponse(
            portfolioId=payload["portfolioId"],
            asOfDate=payload["asOfDate"],
            totalMarketValue=payload["totalMarketValue"],
            positions=payload.get("positions", []),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid lotus-core positions analytics payload: missing {exc}",
        ) from exc


def _workbench_buckets(
    current_positions: list,
    projected_positions: list[WorkbenchProjectedPositionInput],
    group_by: str,
) -> list[WorkbenchAnalyticsBucket]:
    current_map = {row.security_id: row for row in current_positions}
    projected_map = {row.security_id: row for row in projected_positions}
    keys = set(current_map) | set(projected_map)

    grouped: dict[str, dict[str, float | str]] = {}
    current_total = sum(row.quantity for row in current_positions)
    proposed_total = sum(row.proposed_quantity for row in projected_positions) if projected_positions else current_total

    for security_id in keys:
        current_row = current_map.get(security_id)
        projected_row = projected_map.get(security_id)

        if group_by == "SECURITY":
            bucket_key = security_id
            bucket_label = (
                projected_row.instrument_name
                if projected_row
                else (current_row.instrument_name if current_row else security_id)
            )
        else:
            asset_class = (
                projected_row.asset_class if projected_row else (current_row.asset_class if current_row else None)
            )
            bucket_key = str(asset_class or "UNCLASSIFIED").upper()
            bucket_label = bucket_key

        if bucket_key not in grouped:
            grouped[bucket_key] = {
                "bucket_label": bucket_label,
                "current_quantity": 0.0,
                "proposed_quantity": 0.0,
            }

        grouped[bucket_key]["current_quantity"] = float(grouped[bucket_key]["current_quantity"]) + (
            current_row.quantity if current_row else 0.0
        )
        grouped[bucket_key]["proposed_quantity"] = float(grouped[bucket_key]["proposed_quantity"]) + (
            projected_row.proposed_quantity if projected_row else (current_row.quantity if current_row else 0.0)
        )

    buckets: list[WorkbenchAnalyticsBucket] = []
    for key, row in grouped.items():
        current_quantity = float(row["current_quantity"])
        proposed_quantity = float(row["proposed_quantity"])
        buckets.append(
            WorkbenchAnalyticsBucket(
                bucketKey=key,
                bucketLabel=str(row["bucket_label"]),
                currentQuantity=current_quantity,
                proposedQuantity=proposed_quantity,
                deltaQuantity=proposed_quantity - current_quantity,
                currentWeightPct=((current_quantity / current_total) * 100 if current_total > 0 else 0.0),
                proposedWeightPct=((proposed_quantity / proposed_total) * 100 if proposed_total > 0 else 0.0),
            )
        )

    return sorted(buckets, key=lambda item: abs(item.delta_quantity), reverse=True)


def _top_changes(projected_positions: list[WorkbenchProjectedPositionInput]) -> list[WorkbenchTopChange]:
    rows = sorted(projected_positions, key=lambda row: abs(row.delta_quantity), reverse=True)
    return [
        WorkbenchTopChange(
            securityId=row.security_id,
            instrumentName=row.instrument_name,
            deltaQuantity=row.delta_quantity,
            direction="INCREASE" if row.delta_quantity >= 0 else "DECREASE",
        )
        for row in rows[:10]
    ]


@router.post(
    "/workbench",
    response_model=WorkbenchAnalyticsResponse,
    summary="Calculate lotus-performance-owned workbench analytics",
    description=(
        "Returns lotus-performance-owned allocation and top-change analytics "
        "for workbench flows. lotus-gateway passes normalized holdings and projected positions."
    ),
)
async def get_workbench_analytics(request: WorkbenchAnalyticsRequest):
    buckets = _workbench_buckets(
        current_positions=request.current_positions,
        projected_positions=request.projected_positions,
        group_by=request.group_by,
    )
    top_changes = _top_changes(request.projected_positions)

    benchmark_return = (
        request.benchmark_return_pct
        if request.benchmark_return_pct is not None
        else _BENCHMARK_FALLBACK_RETURNS.get(request.benchmark_code, 0.0)
    )
    active_return = (
        request.portfolio_return_pct - benchmark_return
        if request.portfolio_return_pct is not None and benchmark_return is not None
        else None
    )

    return WorkbenchAnalyticsResponse(
        portfolioId=request.portfolio_id,
        period=request.period,
        groupBy=request.group_by,
        benchmarkCode=request.benchmark_code,
        portfolioReturnPct=request.portfolio_return_pct,
        benchmarkReturnPct=benchmark_return,
        activeReturnPct=active_return,
        allocationBuckets=buckets,
        topChanges=top_changes,
    )
