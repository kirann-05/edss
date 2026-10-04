from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import schemas as s
from app.api.deps import Period, State, require, scope_of
from app.core.rbac import Permission
from app.domain.models import AppUser
from app.services import views
from app.services.refresh import RefreshError

router = APIRouter(tags=["data health"])
Reader = Depends(require(Permission.VIEW_DATA_HEALTH))


@router.get("/data-health", response_model=s.DataHealthOut)
def data_health(state: State, period: Period, user: AppUser = Reader) -> s.DataHealthOut:
    return views.build_data_health(state.store, scope_of(user, state), period)


Refresher = Depends(require(Permission.REFRESH_DATA))


@router.post("/data/refresh", response_model=s.RefreshOut)
def refresh(state: State, user: AppUser = Refresher) -> s.RefreshOut:
    """Read the sources again (FR-16). The data in use is replaced only when the whole read worked."""
    if state.settings.edss_database:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "With the database, new data is loaded by make seed-db for now. Refreshing from this "
            "page in database mode is not built yet.",
        )
    if state.runs.any_running():
        # a run reads several times as it goes, and must see one snapshot from start to finish
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A run is in progress. Refresh when it has finished."
        )
    try:
        store, summary = state.data_source.refresh(state.clock())
    except RefreshError as error:
        state.audit.append(
            actor_type="user", actor_id=user.email, action="data.refresh_failed",
            inputs={"by": user.name, "role": user.role.value}, outputs={"reason": str(error)[:300]},
        )  # fmt: skip
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    state.store = store
    state.connector.use_store(store)
    state.audit.append(
        actor_type="user", actor_id=user.email, action="data.refresh",
        inputs={"by": user.name, "role": user.role.value, "source": summary.source},
        outputs={"accepted": summary.accepted, "rejected": summary.rejected, "unchanged_files": summary.unchanged_files},
    )  # fmt: skip
    return s.RefreshOut(
        source=summary.source,  # type: ignore[arg-type]
        folder=summary.folder,
        accepted=summary.accepted,
        rejected=summary.rejected,
        rejects=[s.RejectOut(where=r.ref, why=list(r.reasons)) for r in summary.rejects],
        unchanged_files=summary.unchanged_files,
        periods=list(store.periods),
        current_period=store.current_period,
        refreshed_at=datetime.now(UTC),
    )
