from fastapi import APIRouter

from ....core.config import get_settings
from ....schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(status="ok", version=s.app_version, environment=s.environment)


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    """Readiness probe — could check downstream deps here in the future."""
    s = get_settings()
    return HealthResponse(status="ready", version=s.app_version, environment=s.environment)
