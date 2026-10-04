"""Runs: the interactive loop before the graph, and the graph's execution after (Labs 1, 6, 7).

A person writes a request. The agent asks what it still needs to know, proposes an editable plan,
revises it on feedback, and the person locks it. Only then does the graph run, on a background
thread, so the request returns at once and progress is read from the event log. Clarify and plan
are conversational, so they live here rather than in the batch graph. The lock is the line between
them: after it the plan cannot change.

When the graph reaches the human gate it stops. The decision itself is made by the governance
service, under its own rules, and only a successful decision resumes the graph.
"""

import functools
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from langgraph.types import Command

from app.agents.connector import Connector
from app.agents.graph import initial_state, run_config
from app.agents.llm import ChatModel
from app.agents.models import Clarification, ClarifyQuestion, Plan
from app.agents.runtime import RunEvents
from app.agents.skills.plan_skill import (
    KpiInfo,
    PlanCatalogue,
    PlanError,
    apply_patch,
    clarify,
    diff_plans,
    lock_plan,
    propose_plan,
    revise_plan,
)
from app.agents.validation.faults import FAULTS
from app.domain.models import AppUser
from app.governance.audit import AuditLog
from app.mcp_connector.context import reading_through
from app.services.system_config import SystemConfig


class RunStatus(StrEnum):
    CLARIFYING = "clarifying"  # the agent still has questions
    PLANNING = "planning"  # a plan exists and can be edited
    RUNNING = "running"  # the plan is locked and the graph is working
    AWAITING_REVIEW = "awaiting_review"  # stopped at the human gate
    COMPLETED = "completed"
    FAILED = "failed"


SETTLED = (RunStatus.AWAITING_REVIEW, RunStatus.COMPLETED, RunStatus.FAILED)


class RunError(Exception):
    pass


class RunNotFound(RunError):
    pass


@dataclass
class RunRecord:
    id: str
    request: str
    created_by: str  # email
    created_by_name: str
    created_at: datetime
    status: RunStatus = RunStatus.CLARIFYING
    questions: list[ClarifyQuestion] = field(default_factory=list)  # still waiting for an answer
    asked: dict[str, ClarifyQuestion] = field(default_factory=dict)  # every question ever asked
    answers: list[Clarification] = field(default_factory=list)
    plan: Plan | None = None
    plan_history: list[dict[str, Any]] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    brief_id: str | None = None
    error: str | None = None
    reads_direct: bool = False  # the demo's ready-made runs, seeded before the server can answer


def _persists(method):
    """Write the run through to the store once the change is made."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        record = result[0] if isinstance(result, tuple) else result
        if not isinstance(record, RunRecord):
            record = self.get(kwargs.get("run_id") or next(a for a in args if isinstance(a, str)))
        self._persist(record)
        return result

    return wrapper


class RunService:
    def __init__(
        self,
        *,
        model: ChatModel,
        graph: Any,
        catalogue: Callable[[], PlanCatalogue],
        audit: AuditLog,
        events: RunEvents,
        system_config: SystemConfig,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        synchronous: bool = False,
        open_reads: Callable[[RunRecord], AbstractContextManager[Connector]] | None = None,
        direct: Connector | None = None,
        store: Any = None,
    ) -> None:
        """`open_reads` gives each run its own connector session, opened on the run's thread for
        as long as the graph works. Without it the graph reads through what it was built with."""
        self._model = model
        self._graph = graph
        self._catalogue = catalogue
        self._audit = audit
        self._events = events
        self._config = system_config
        self._clock = clock
        self._synchronous = synchronous
        self._open_reads = open_reads
        self._direct = direct
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.RLock()
        # with a store (app/db/work_store.py) runs are restored from it and every change is
        # written through (decision D31). A run that was working when the server stopped is
        # marked stopped, never shown as still running
        self._store = store
        if store is not None:
            for record in store.load():
                if record.status is RunStatus.RUNNING:
                    record.status = RunStatus.FAILED
                    record.error = "Stopped when the server restarted. Resume carries it on."
                    store.save(record)
                self._runs[record.id] = record

    def _persist(self, record: RunRecord) -> None:
        if self._store is not None:
            with self._lock:  # one save at a time, each of the state as it is now
                self._store.save(record)

    # --- lookups ----------------------------------------------------------------------------
    def get(self, run_id: str) -> RunRecord:
        with self._lock:
            try:
                return self._runs[run_id]
            except KeyError:
                raise RunNotFound(f"there is no run {run_id!r}") from None

    def runs(self) -> list[RunRecord]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    def any_running(self) -> bool:
        with self._lock:
            return any(r.status is RunStatus.RUNNING for r in self._runs.values())

    def is_settled(self, run_id: str) -> bool:
        return self.get(run_id).status in SETTLED

    # --- the conversation before the lock ---------------------------------------------------
    @_persists
    def create(self, user: AppUser, request: str) -> RunRecord:
        request = request.strip()
        if len(request) < 3:
            raise RunError("Say what you want the brief to cover")
        with self._lock:
            record = RunRecord(
                id=f"run-{len(self._runs) + 1}",
                request=request,
                created_by=user.email,
                created_by_name=user.name,
                created_at=self._clock(),
            )
            self._runs[record.id] = record
            self._ask(record)
        self._log_user(
            user,
            "run.create",
            record,
            {"request": request},
            {"questions": [q.id for q in record.questions]},
        )
        return record

    def _ask(self, record: RunRecord) -> None:
        catalogue = self._catalogue()
        remaining = clarify(self._model, record.request, record.answers, catalogue)
        record.questions = remaining
        record.asked.update({q.id: q for q in remaining})
        if remaining:
            record.status = RunStatus.CLARIFYING
        else:
            self._propose(record, catalogue)

    def _propose(self, record: RunRecord, catalogue: PlanCatalogue) -> None:
        record.questions = []
        record.plan = propose_plan(self._model, record.request, record.answers, catalogue)
        record.plan_history.append(
            {"revision": 1, "changes": ["First proposal"], "at": self._clock().isoformat()}
        )
        record.status = RunStatus.PLANNING

    @_persists
    def answer(self, user: AppUser, run_id: str, answers: list[Clarification]) -> RunRecord:
        with self._lock:
            record = self._open(run_id, RunStatus.CLARIFYING)
            known = {q.id for q in record.questions}
            unknown = [a.question_id for a in answers if a.question_id not in known]
            if unknown:
                raise RunError(f"there is no question {unknown[0]!r} to answer")
            merged = {a.question_id: a for a in record.answers}
            merged.update({a.question_id: a for a in answers if a.answer.strip()})
            record.answers = list(merged.values())
            self._ask(record)
        self._log_user(
            user,
            "run.answer",
            record,
            {"answers": [a.question_id for a in answers]},
            {"status": record.status.value},
        )
        return record

    @_persists
    def skip_questions(self, user: AppUser, run_id: str) -> RunRecord:
        """Go on with what is known. Anything unanswered gets a plain default in the plan."""
        with self._lock:
            record = self._open(run_id, RunStatus.CLARIFYING)
            self._propose(record, self._catalogue())
        self._log_user(user, "run.skip_questions", record, {}, {"status": record.status.value})
        return record

    @_persists
    def edit_plan(self, user: AppUser, run_id: str, patch: dict[str, Any]) -> RunRecord:
        with self._lock:
            record = self._open(run_id, RunStatus.PLANNING)
            before = record.plan
            assert before is not None
            catalogue = self._catalogue()
            record.plan = self._plan_call(lambda: apply_patch(before, patch, catalogue))
            changes = diff_plans(before, record.plan, catalogue)
            if record.plan.steps != before.steps:
                changes.append("Reworded the outline")
            record.plan_history.append(
                {
                    "revision": record.plan.revision,
                    "changes": changes or ["Saved with no change"],
                    "at": self._clock().isoformat(),
                }
            )
        self._log_user(
            user,
            "plan.edit",
            record,
            {"patch": patch},
            {"revision": record.plan.revision, "changes": changes},
        )
        return record

    @_persists
    def revise_plan(self, user: AppUser, run_id: str, feedback: str) -> tuple[RunRecord, list[str]]:
        if not feedback.strip():
            raise RunError("Say what you would like changed")
        with self._lock:
            record = self._open(run_id, RunStatus.PLANNING)
            assert record.plan is not None
            revised, changes = self._plan_call(
                lambda: revise_plan(self._model, record.plan, feedback, self._catalogue())
            )
            record.plan = revised
            record.plan_history.append(
                {"revision": revised.revision, "changes": changes, "at": self._clock().isoformat()}
            )
        self._log_user(
            user,
            "plan.revise",
            record,
            {"feedback": feedback},
            {"changes": changes, "revision": revised.revision},
        )
        return record, changes

    def _plan_call(self, call: Callable[[], Any]) -> Any:
        try:
            return call()
        except PlanError as error:
            raise RunError(str(error)) from None

    def _open(self, run_id: str, expected: RunStatus) -> RunRecord:
        record = self.get(run_id)
        if record.status is not expected:
            raise RunError(f"this run is {record.status.value}, so that is not possible now")
        return record

    # --- the lock and the run ---------------------------------------------------------------
    @_persists
    def lock(
        self,
        user: AppUser,
        run_id: str,
        faults: list[str] | None = None,
        *,
        reads_direct: bool = False,
    ) -> RunRecord:
        """`reads_direct` is for code that runs before the server can answer its own connector
        endpoint, which today means seeding the demo. No route passes it."""
        faults = list(faults or [])
        with self._lock:
            record = self._open(run_id, RunStatus.PLANNING)
            assert record.plan is not None
            if faults and self._config.data_mode() != "synthetic":
                raise RunError("failure injection is only available with synthetic data")
            unknown = [f for f in faults if f not in FAULTS]
            if unknown:
                raise RunError(f"unknown fault {unknown[0]!r}")
            record.plan = self._plan_call(lambda: lock_plan(record.plan, self._clock()))
            record.faults = faults
            record.reads_direct = reads_direct
            record.status = RunStatus.RUNNING
        self._log_user(
            user,
            "plan.lock",
            record,
            {"plan": record.plan.model_dump(mode="json")},
            {
                "locked_at": record.plan.locked_at,
                "kpis": len(record.plan.kpi_keys),
                "faults": faults,
            },
        )
        self._events.emit(record.id, "run", "Plan locked, run started", "running")
        self._launch(record.id, initial_state(record.id, record.plan, user.email, faults))
        return record

    @_persists
    def resume(self, user: AppUser, run_id: str) -> RunRecord:
        """Continue a run that stopped, from its last checkpoint (FR-13)."""
        with self._lock:
            record = self._open(run_id, RunStatus.FAILED)
            record.status, record.error = RunStatus.RUNNING, None
        self._log_user(user, "run.resume", record, {}, {})
        self._events.emit(record.id, "run", "Resuming from the last checkpoint", "running")
        self._launch(record.id, None)
        return record

    @_persists
    def on_decision(self, run_id: str, status: str, version: int | None, by: str) -> None:
        """A person has decided, under the governance rules. Let the graph record it and finish."""
        with self._lock:
            record = self.get(run_id)
            record.status = RunStatus.RUNNING
        self._launch(run_id, Command(resume={"status": status, "version": version, "by": by}))

    # --- execution ---------------------------------------------------------------------------
    def _launch(self, run_id: str, payload: Any) -> None:
        if self._synchronous:
            self._execute(run_id, payload)
            return
        threading.Thread(
            target=self._execute, args=(run_id, payload), daemon=True, name=f"run-{run_id}"
        ).start()

    def _execute(self, run_id: str, payload: Any) -> None:
        record = self.get(run_id)
        try:
            self._run_graph(run_id, payload, record)
        finally:
            self._persist(record)

    def _run_graph(self, run_id: str, payload: Any, record: RunRecord) -> None:
        config = run_config(run_id)
        try:
            with self._reads(record):
                result = self._graph.invoke(payload, config)
            state = self._graph.get_state(config).values
            with self._lock:
                record.brief_id = state.get("brief_id", record.brief_id)
                if "__interrupt__" in result:
                    record.status = RunStatus.AWAITING_REVIEW
                else:
                    record.status = RunStatus.COMPLETED
            if "__interrupt__" in result:
                self._events.emit(run_id, "human_gate", "Waiting for a person to review", "waiting")
                self._audit.append(
                    actor_type="system", actor_id="runtime", action="gate.waiting", run_id=run_id,
                    inputs={}, outputs={"brief_id": record.brief_id, "escalated": state.get("escalated", False)},
                )  # fmt: skip
            else:
                self._events.emit(run_id, "run", "Run complete", "done")
        except Exception as error:
            with self._lock:
                record.status, record.error = RunStatus.FAILED, str(error)
            self._events.emit(run_id, "run", "Run stopped", "failed", detail=str(error))
            self._audit.append(
                actor_type="system", actor_id="runtime", action="run.failed", run_id=run_id,
                inputs={}, outputs={"error": str(error), "error_type": type(error).__name__},
            )  # fmt: skip

    @contextmanager
    def _reads(self, record: RunRecord) -> Iterator[None]:
        if self._open_reads is None:
            yield
            return
        if record.reads_direct:
            assert self._direct is not None
            with reading_through(self._direct):
                yield
            return
        with self._open_reads(record) as connector, reading_through(connector):
            yield

    def _log_user(
        self,
        user: AppUser,
        action: str,
        record: RunRecord,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
    ) -> None:
        self._audit.append(
            actor_type="user",
            actor_id=user.email,
            action=action,
            run_id=record.id,
            inputs={"by": user.name, "role": user.role.value, **inputs},
            outputs=outputs,
        )


def plan_catalogue_from(connector: Any) -> PlanCatalogue:
    return PlanCatalogue(
        periods=connector.periods(),
        current_period=connector.current_period(),
        kpis=tuple(
            KpiInfo(key=d.key, name=d.name, domain=d.domain)
            for d in connector.get_kpi_definitions()
        ),
    )
