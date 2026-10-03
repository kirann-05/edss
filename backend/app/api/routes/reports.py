"""Published reports: versions, the current pointer, diff and rollback (FR-9, FR-14)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import schemas as s
from app.api.deps import AppState, CurrentUser, State, require
from app.core.rbac import Permission
from app.domain.models import AppUser
from app.governance.service import GovernanceError
from app.services import brief_views
from app.services.validation_context import context_for_document

router = APIRouter(tags=["reports"])
Reader = Depends(require(Permission.VIEW_REPORTS))


def _version(state: AppState, number: int):
    try:
        return state.governance.version(number)
    except GovernanceError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no version {number}") from None


@router.get("/reports/current", response_model=s.CurrentReportOut)
def current(state: State, user: AppUser = Reader) -> s.CurrentReportOut:
    version = state.governance.current()
    return s.CurrentReportOut(
        current=brief_views.version_out(version, state.governance.state_of(version.version))
        if version
        else None
    )


@router.get("/reports/versions", response_model=list[s.VersionOut])
def versions(state: State, user: AppUser = Reader) -> list[s.VersionOut]:
    gov = state.governance
    return [brief_views.version_out(v, gov.state_of(v.version)) for v in reversed(gov.versions())]


@router.get("/reports/versions/{number}", response_model=s.VersionDetailOut)
def version_detail(number: int, state: State, user: AppUser = Reader) -> s.VersionDetailOut:
    version = _version(state, number)
    ctx = context_for_document(version.document, state.connector, approval_present=True)
    return brief_views.version_detail(version, state.governance.state_of(number), ctx)


@router.get("/reports/diff", response_model=s.DiffOut)
def diff(
    state: State,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
    user: AppUser = Reader,
) -> s.DiffOut:
    _version(state, from_version)
    _version(state, to_version)
    changes = state.governance.diff(from_version, to_version)
    return s.DiffOut(
        from_version=from_version,
        to_version=to_version,
        changes=[
            s.ChangeOut(
                section=c.section, kind=c.kind, kpi_key=c.kpi_key, option_id=c.option_id,
                field=c.field, before=c.before, after=c.after,
            )
            for c in changes
        ],
    )  # fmt: skip


@router.post("/reports/rollback", response_model=s.VersionOut)
def rollback(body: s.RollbackIn, state: State, user: CurrentUser) -> s.VersionOut:
    """Move the current pointer back. The governance service checks the role and keeps history intact."""
    version = state.governance.rollback(user, body.to_version, body.reason)
    return brief_views.version_out(version, state.governance.state_of(version.version))
