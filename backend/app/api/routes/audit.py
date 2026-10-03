"""The audit viewer (FR-12): every step and every decision, with the chain's verification."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from app.api import schemas as s
from app.api.deps import State, require
from app.core.rbac import Permission
from app.domain.models import AppUser
from app.governance.audit import AuditRow

router = APIRouter(tags=["audit"])
Auditor = Depends(require(Permission.VIEW_AUDIT))


def row_out(row: AuditRow) -> s.AuditRowOut:
    return s.AuditRowOut(
        id=row.id, ts=row.ts, run_id=row.run_id, actor_type=row.actor_type, actor_id=row.actor_id,
        action=row.action, inputs=row.inputs, outputs=row.outputs, prev_hash=row.prev_hash, hash=row.hash,
    )  # fmt: skip


@router.get("/audit", response_model=s.AuditPageOut)
def audit_rows(
    state: State,
    run_id: str | None = None,
    actor: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: AppUser = Auditor,
) -> s.AuditPageOut:
    """Newest first. Filtering never changes what the chain check covers."""
    # a time without a zone is read as UTC, so it can be compared with the log's own times
    since, until = (t.replace(tzinfo=UTC) if t and t.tzinfo is None else t for t in (since, until))
    rows = state.audit.rows(run_id=run_id, actor_id=actor, action=action, since=since, until=until)
    rows.reverse()
    return s.AuditPageOut(
        rows=[row_out(r) for r in rows[offset : offset + limit]],
        total=len(rows),
        offset=offset,
        limit=limit,
    )


@router.get("/audit/verify", response_model=s.VerifyOut)
def verify(state: State, user: AppUser = Auditor) -> s.VerifyOut:
    result = state.audit.verify()
    return s.VerifyOut(
        ok=result.ok, checked=result.checked, broken_at=result.broken_at, reason=result.reason
    )


@router.get("/audit/actions", response_model=list[str])
def actions(state: State, user: AppUser = Auditor) -> list[str]:
    return state.audit.actions()
