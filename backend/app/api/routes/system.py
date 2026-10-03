from fastapi import APIRouter, Depends

from app import __version__
from app.api import schemas as s
from app.api.deps import State, current_user

router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(current_user)])


@router.get("/status", response_model=s.SystemStatusOut)
def status(state: State) -> s.SystemStatusOut:
    settings = state.settings
    return s.SystemStatusOut(
        version=__version__,
        data_mode=settings.data_mode,
        llm_provider=settings.llm_provider,
        llm_is_fake=settings.llm_provider == "fake",
        current_period=state.store.current_period,
        periods=list(state.store.periods),
        today=state.store.today,
        stale_after_days=state.store.stale_after_days,
        simulated_source_latency_ms=settings.source_latency_ms,
    )
