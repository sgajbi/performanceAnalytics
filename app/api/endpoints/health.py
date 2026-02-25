from fastapi import APIRouter, Request, Response, status

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/live", summary="Service liveness")
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready", summary="Service readiness")
async def health_ready(request: Request, response: Response) -> dict[str, str]:
    if bool(getattr(request.app.state, "is_draining", False)):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "draining"}
    return {"status": "ready"}
