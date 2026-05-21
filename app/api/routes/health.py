from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "repository_backend": settings.repository_backend,
        "store_ready": hasattr(request.app.state, "store"),
        "request_id": getattr(request.state, "request_id", None),
        "correlation_id": getattr(request.state, "correlation_id", None),
    }
