"""Demo housekeeping. It does not exist outside demo mode, which needs synthetic data."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import State, require
from app.core.rbac import Permission
from app.domain.models import AppUser

router = APIRouter(prefix="/demo", tags=["demo"])
Resetter = Depends(require(Permission.REFRESH_DATA))


@router.post("/reset")
def reset(request: Request, state: State, user: AppUser = Resetter) -> dict:
    """Start the demo again from its ready-made state. Everything made since is discarded."""
    if not state.demo_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if state.settings.edss_database:
        # the audit log there is append-only, so a reset cannot take the demo back to its start
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The demo reset works with in-memory data only. With the database, everything stays.",
        )
    fresh = request.app.state.edss_factory()
    fresh.audit.append(
        actor_type="user", actor_id=user.email, action="demo.reset",
        inputs={"by": user.name, "role": user.role.value}, outputs={},
    )  # fmt: skip
    request.app.state.edss = fresh
    return {"reset": True, "seeded": fresh.settings.edss_demo_state}
