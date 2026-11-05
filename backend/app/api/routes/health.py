from fastapi import APIRouter
from ...schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Report API availability only; does not check a database."""
    return HealthResponse()
