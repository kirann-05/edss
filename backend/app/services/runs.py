"""Runs: the interactive loop before the graph, and the graph's execution after (Labs 1, 6, 7).

A person writes a request. The agent asks what it still needs to know, proposes an editable plan,
revises it on feedback, and the person locks it. Only then does the graph run, on a background
thread, so the request returns at once and progress is read from the event log. Clarify and plan
are conversational, so they live here rather than in the batch graph. The lock is the line between
them: after it the plan cannot change.

When the graph reaches the human gate it stops. The decision itself is made by the governance
service, under its own rules, and only a successful decision resumes the graph.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from langgraph.types import Command

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
    lock_plan,
    propose_plan,
    revise_plan,
)
from app.agents.validation.faults import FAULTS
from app.domain.models import AppUser
from app.governance.audit import AuditLog
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
    questions: list[ClarifyQuestion] = field(default_factory=list)
    answers: list[Clarification] = field(default_factory=list)
    plan: Plan | None = None
    plan_history: list[dict[str, Any]] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    brief_id: str | None = None
    error: str | None = None


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
    ) -> None:
        self._model = model
        self._graph = graph
        self._catalogue = catalogue
        self._audit = audit
        self._events = events
        self._config = system_config
        self._clock = clock
        self._synchronous = synchronous
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.RLock()

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

    def is_settled(self, run_id: str) -> bool:
        return self.get(run_id).status in SETTLED

    # --- the conversation before the lock ---------------------------------------------------
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

    def skip_questions(self, user: AppUser, run_id: str) -> RunRecord:
        """Go on with what is known. Anything unanswered gets a plain default in the plan."""
        with self._lock:
            record = self._open(run_id, RunStatus.CLARIFYING)
            self._propose(record, self._catalogue())
        self._log_user(user, "run.skip_questions", record, {}, {"status": record.status.value})
        return record

    def edit_plan(self, user: AppUser, run_id: str, patch: dict[str, Any]) -> RunRecord:
        with self._lock:
            record = self._open(run_id, RunStatus.PLANNING)
            assert record.plan is not None
            record.plan = self._plan_call(
                lambda: apply_patch(record.plan, patch, self._catalogue())
            )
            record.plan_history.append(
                {
                    "revision": record.plan.revision,
                    "changes": ["Edited directly"],
                    "at": self._clock().isoformat(),
                }
            )
        self._log_user(
            user, "plan.edit", record, {"patch": patch}, {"revision": record.plan.revision}
        )
        return record

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
    def lock(self, user: AppUser, run_id: str, faults: list[str] | None = None) -> RunRecord:
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

    def resume(self, user: AppUser, run_id: str) -> RunRecord:
        """Continue a run that stopped, from its last checkpoint (FR-13)."""
        with self._lock:
            record = self._open(run_id, RunStatus.FAILED)
            record.status, record.error = RunStatus.RUNNING, None
        self._log_user(user, "run.resume", record, {}, {})
        self._events.emit(record.id, "run", "Resuming from the last checkpoint", "running")
        self._launch(record.id, None)
        return record

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
        config = run_config(run_id)
        record = self.get(run_id)
        try:
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
