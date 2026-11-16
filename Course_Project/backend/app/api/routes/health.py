from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import DataMode, get_settings

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    data_mode: DataMode


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="edss-backend",
        version=__version__,
        data_mode=settings.data_mode,
    )
