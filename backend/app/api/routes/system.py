from fastapi import APIRouter, Depends

from app import __version__
from app.agents.llm import is_local_host
from app.api import schemas as s
from app.api.deps import State, current_user

router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(current_user)])


@router.get("/status", response_model=s.SystemStatusOut)
def status(state: State) -> s.SystemStatusOut:
    settings = state.settings
    fake = settings.llm_provider == "fake"
    local_hosts = tuple(h.strip().lower() for h in settings.llm_local_hosts.split(",") if h.strip())
    ping = getattr(state.drafter, "reachable", None)
    return s.SystemStatusOut(
        version=__version__,
        data_mode=settings.data_mode,
        llm_provider=settings.llm_provider,
        llm_is_fake=fake,
        llm_name=getattr(state.drafter, "name", settings.llm_provider),
        llm_is_local=fake or is_local_host(settings.llm_base_url, local_hosts),
        llm_reachable=None if fake or not callable(ping) else bool(ping()),
        current_period=state.store.current_period,
        periods=list(state.store.periods),
        today=state.store.today,
        stale_after_days=state.store.stale_after_days,
        simulated_source_latency_ms=settings.source_latency_ms,
    )
