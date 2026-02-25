from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live", summary="Service liveness")
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready", summary="Service readiness")
async def health_ready() -> dict[str, str]:
    return {"status": "ready"}
