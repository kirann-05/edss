"""Draft briefs and the human gate (FR-8). Reviewers read, approvers decide."""

from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.validation.suite import validate
from app.api import schemas as s
from app.api.deps import AppState, CurrentUser, State, require
from app.core.rbac import Permission
from app.domain.enums import BriefStatus
from app.domain.models import AppUser
from app.governance.service import (
    BriefRecord,
    Decision,
    EditRequest,
    GovernanceError,
    apply_edits,
)
from app.services import brief_views
from app.services.runs import RunNotFound
from app.services.validation_context import context_for_document

router = APIRouter(tags=["briefs"])
Reviewer = Depends(require(Permission.REVIEW))


def _request_text(state: AppState, record: BriefRecord) -> str | None:
    try:
        return state.runs.get(record.run_id).request
    except RunNotFound:
        return None


def _record(state: AppState, brief_id: str) -> BriefRecord:
    try:
        return state.governance.get(brief_id)
    except GovernanceError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no brief {brief_id!r}") from None


def _brief_out(state: AppState, record: BriefRecord, user: AppUser) -> s.BriefOut:
    return brief_views.brief_out(
        record,
        _request_text(state, record),
        state.governance.approval_state(record.id),
        user,
        context_for_document(
            record.document, state.connector, approval_present=record.approval is not None
        ),
    )


@router.get("/briefs", response_model=list[s.BriefSummaryOut])
def list_briefs(
    state: State, status_filter: BriefStatus | None = None, user: AppUser = Reviewer
) -> list[s.BriefSummaryOut]:
    records = sorted(
        state.governance.briefs(status_filter), key=lambda r: r.created_at, reverse=True
    )
    return [brief_views.brief_summary(r, _request_text(state, r)) for r in records]


@router.get("/briefs/{brief_id}", response_model=s.BriefOut)
def get_brief(brief_id: str, state: State, user: AppUser = Reviewer) -> s.BriefOut:
    return _brief_out(state, _record(state, brief_id), user)


@router.get("/briefs/{brief_id}/evidence", response_model=list[s.EvidenceRowOut])
def evidence(brief_id: str, state: State, user: AppUser = Reviewer) -> list[s.EvidenceRowOut]:
    return brief_views.evidence_rows(_record(state, brief_id).document, state.connector)


@router.get("/briefs/{brief_id}/prior", response_model=list[s.PriorMatchOut])
def prior(brief_id: str, state: State, user: AppUser = Reviewer) -> list[s.PriorMatchOut]:
    matches = state.archive.similar(_record(state, brief_id).document, exclude_brief=brief_id)
    return [
        s.PriorMatchOut(
            id=m.brief.id, period_year=m.brief.period_year, title=m.brief.title,
            decided_on=m.brief.decided_on, decision=m.brief.decision,
            matching_kpis=m.matching_kpis, score=m.score, reason=m.reason,
        )
        for m in matches
    ]  # fmt: skip


def _requests(edits: list[s.EditRequestIn]) -> tuple[EditRequest, ...]:
    return tuple(EditRequest(option_id=e.option_id, field=e.field, value=e.value) for e in edits)


@router.post("/briefs/{brief_id}/check-edits", response_model=s.EditCheckOut)
def check_edits(
    brief_id: str, body: s.EditCheckIn, state: State, user: AppUser = Reviewer
) -> s.EditCheckOut:
    """A dry run: would these edits pass validation? Nothing is saved or published."""
    record = _record(state, brief_id)
    try:
        document, _ = apply_edits(
            record.document, _requests(body.edits), user.name, record.created_at
        )
    except GovernanceError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None
    return s.EditCheckOut(
        report=validate(document, context_for_document(document, state.connector))
    )


@router.post("/briefs/{brief_id}/decision", response_model=s.DecisionOut)
def decide(brief_id: str, body: s.DecisionIn, state: State, user: CurrentUser) -> s.DecisionOut:
    """Approve, edit, override or send back. The governance service checks the role, and logs a
    refusal as well as a success, so this route needs only a signed-in person."""
    _record(state, brief_id)
    decision = Decision(
        kind=body.kind,
        reason=body.reason,
        edits=_requests(body.edits),
        ack_escalation=body.ack_escalation,
    )
    result = state.governance.decide(brief_id, user, decision)
    # the decision stands and is audited, so a missing run record cannot undo it
    with suppress(RunNotFound):
        state.runs.on_decision(
            result.brief.run_id, result.brief.status.value, result.brief.version, user.name
        )
    return s.DecisionOut(
        brief=_brief_out(state, state.governance.get(brief_id), user), version=result.brief.version
    )
