"""Runs: ask, plan, lock, watch. A run belongs to whoever started it, and to the reviewers."""

import json
from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.agents.models import Clarification
from app.agents.runtime import RunEvent
from app.agents.skills.plan_skill import AREAS, AUDIENCES
from app.agents.validation.faults import FAULT_INFO, FAULTS
from app.api import schemas as s
from app.api.deps import AppState, State, require
from app.core.rbac import Permission, has_permission
from app.domain.models import AppUser
from app.services.runs import RunNotFound, RunRecord

router = APIRouter(tags=["runs"])
Starter = Depends(require(Permission.START_RUN))
Auditor = Depends(require(Permission.VIEW_AUDIT))


def event_out(e: RunEvent) -> s.RunEventOut:
    return s.RunEventOut(
        id=e.id, ts=e.ts, node=e.node, label=e.label, state=e.state,  # type: ignore[arg-type]
        elapsed_ms=e.elapsed_ms, attempt=e.attempt, detail=e.detail, ok=e.ok,
    )  # fmt: skip


def run_out(record: RunRecord) -> s.RunOut:
    plan = record.plan
    return s.RunOut(
        id=record.id,
        request=record.request,
        status=record.status,
        created_by_name=record.created_by_name,
        created_at=record.created_at,
        questions=[
            s.QuestionOut(id=q.id, text=q.text, why=q.why, choices=list(q.choices))
            for q in record.questions
        ],
        answers=[
            s.AnswerOut(
                question_id=a.question_id,
                question=record.asked[a.question_id].text
                if a.question_id in record.asked
                else a.question_id,
                answer=a.answer,
            )
            for a in record.answers
        ],
        plan=(
            s.PlanOut(
                request=plan.request,
                period_year=plan.period_year,
                domains=list(plan.domains),
                kpi_keys=list(plan.kpi_keys),
                options_for=plan.options_for,
                audience=plan.audience,
                steps=[s.PlanStepOut(id=x.id, title=x.title, detail=x.detail) for x in plan.steps],
                revision=plan.revision,
                locked_at=plan.locked_at,
            )
            if plan
            else None
        ),
        plan_history=[s.PlanHistoryOut(**h) for h in record.plan_history],
        faults=record.faults,
        brief_id=record.brief_id,
        error=record.error,
    )


def visible_run(state: AppState, user: AppUser, run_id: str) -> RunRecord:
    """A person sees their own runs. Reviewers see every run. Anyone else gets a plain 404."""
    try:
        record = state.runs.get(run_id)
    except RunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no run {run_id!r}") from None
    if record.created_by != user.email and not has_permission(user, Permission.REVIEW):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no run {run_id!r}")
    return record


@router.get("/plan-catalogue", response_model=s.PlanCatalogueOut)
def plan_catalogue(state: State, user: AppUser = Starter) -> s.PlanCatalogueOut:
    connector = state.connector
    synthetic = state.system_config.data_mode() == "synthetic"
    return s.PlanCatalogueOut(
        periods=list(connector.periods()),
        current_period=connector.current_period(),
        domains=list(AREAS),
        kpis=[
            s.KpiChoiceOut(key=d.key, name=d.name, domain=d.domain)
            for d in connector.get_kpi_definitions()
        ],
        audiences=list(AUDIENCES),
        faults=[
            s.FaultOut(id=f, label=FAULT_INFO[f][0], description=FAULT_INFO[f][1]) for f in FAULTS
        ]
        if synthetic
        else [],
    )


@router.post("/runs", response_model=s.RunOut, status_code=status.HTTP_201_CREATED)
def create_run(body: s.CreateRunIn, state: State, user: AppUser = Starter) -> s.RunOut:
    return run_out(state.runs.create(user, body.request))


@router.get("/runs", response_model=list[s.RunOut])
def list_runs(state: State, user: AppUser = Starter) -> list[s.RunOut]:
    reviewer = has_permission(user, Permission.REVIEW)
    return [run_out(r) for r in state.runs.runs() if reviewer or r.created_by == user.email]


@router.get("/runs/{run_id}", response_model=s.RunOut)
def get_run(run_id: str, state: State, user: AppUser = Starter) -> s.RunOut:
    return run_out(visible_run(state, user, run_id))


@router.post("/runs/{run_id}/answers", response_model=s.RunOut)
def answer(run_id: str, body: s.AnswersIn, state: State, user: AppUser = Starter) -> s.RunOut:
    visible_run(state, user, run_id)
    answers = [Clarification(question_id=a.question_id, answer=a.answer) for a in body.answers]
    return run_out(state.runs.answer(user, run_id, answers))


@router.post("/runs/{run_id}/skip-questions", response_model=s.RunOut)
def skip_questions(run_id: str, state: State, user: AppUser = Starter) -> s.RunOut:
    visible_run(state, user, run_id)
    return run_out(state.runs.skip_questions(user, run_id))


@router.put("/runs/{run_id}/plan", response_model=s.RunOut)
def edit_plan(run_id: str, body: s.PlanPatchIn, state: State, user: AppUser = Starter) -> s.RunOut:
    visible_run(state, user, run_id)
    patch = body.model_dump(exclude_none=True, mode="json")
    return run_out(state.runs.edit_plan(user, run_id, patch))


@router.post("/runs/{run_id}/plan/revise", response_model=s.RunRevisionOut)
def revise_plan(
    run_id: str, body: s.ReviseIn, state: State, user: AppUser = Starter
) -> s.RunRevisionOut:
    visible_run(state, user, run_id)
    record, changes = state.runs.revise_plan(user, run_id, body.feedback)
    return s.RunRevisionOut(run=run_out(record), changes=changes)


@router.post("/runs/{run_id}/plan/lock", response_model=s.RunOut)
def lock_plan(run_id: str, body: s.LockIn, state: State, user: AppUser = Starter) -> s.RunOut:
    visible_run(state, user, run_id)
    return run_out(state.runs.lock(user, run_id, body.faults))


@router.post("/runs/{run_id}/resume", response_model=s.RunOut)
def resume(run_id: str, state: State, user: AppUser = Starter) -> s.RunOut:
    visible_run(state, user, run_id)
    return run_out(state.runs.resume(user, run_id))


def _sse(event: RunEvent) -> str:
    return f"id: {event.id}\nevent: node\ndata: {json.dumps(event_out(event).model_dump(mode='json'))}\n\n"


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    state: State,
    after: int = Query(0, ge=0),
    user: AppUser = Starter,
) -> StreamingResponse:
    """Live progress as server-sent events. A reconnect resumes from Last-Event-ID."""
    visible_run(state, user, run_id)
    resume_from = request.headers.get("last-event-id")
    last = max(after, int(resume_from)) if resume_from and resume_from.isdigit() else after

    async def stream() -> AsyncIterator[str]:
        nonlocal last
        quiet = 0.0
        while True:
            batch = await anyio.to_thread.run_sync(state.events.wait, run_id, last, 1.0)
            for event in batch:
                last = event.id
                yield _sse(event)
            quiet = 0.0 if batch else quiet + 1.0
            if await request.is_disconnected():
                return
            settled = not batch and state.runs.is_settled(run_id)
            if settled and not state.events.since(run_id, last):  # nothing more is coming
                record = state.runs.get(run_id)
                yield f"event: end\ndata: {json.dumps({'status': record.status.value})}\n\n"
                return
            if quiet >= 15:  # keep proxies from closing an idle stream
                yield ": keepalive\n\n"
                quiet = 0.0

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/trace", response_model=s.TraceOut)
def trace(run_id: str, state: State, user: AppUser = Auditor) -> s.TraceOut:
    try:
        state.runs.get(run_id)
    except RunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no run {run_id!r}") from None
    from app.api.routes.audit import row_out

    return s.TraceOut(
        run_id=run_id,
        events=[event_out(e) for e in state.events.all(run_id)],
        audit=[row_out(r) for r in state.audit.rows(run_id=run_id)],
    )
