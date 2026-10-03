"""The runtime around the graph (Lab 6): audit, events, timing and a budget for every step.

Every node runs through `Runtime.traced`, so no step can happen without leaving a row in the
audit log with its inputs and outputs (rule 9), an event the UI shows live, and a check against
the run's time budget. The coordinator is the graph plus this wrapper. It is not a separate model,
because control logic gains nothing from one and risks a lot (decision D10).

Agents depend on the small protocols here and never import the audit log or the governance
service directly, so the graph can be tested with simple stand-ins.
"""

import functools
import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from app.agents.models import BriefDocument, ValidationReport
from app.core.canonical import canonical

NodeState = Literal["running", "done", "failed", "waiting"]


class AuditSink(Protocol):
    def append(
        self,
        *,
        actor_type: Literal["user", "agent", "system"],
        actor_id: str,
        action: str,
        inputs: dict[str, Any] | None = ...,
        outputs: dict[str, Any] | None = ...,
        run_id: str | None = ...,
    ) -> Any: ...


class DraftSink(Protocol):
    """Where a finished draft goes to wait for a person. It returns the brief's id."""

    def __call__(
        self,
        *,
        run_id: str,
        document: BriefDocument,
        validation: ValidationReport,
        attempts: int,
        escalated: bool,
        diagnosis: str | None,
        repair_log: tuple[str, ...],
        history: tuple[ValidationReport, ...],
        created_by: str,
    ) -> str: ...


class BudgetExceeded(RuntimeError):
    """The run used more time than it was given (rule 8: never run forever)."""


@dataclass(frozen=True)
class RunEvent:
    id: int
    ts: datetime
    run_id: str
    node: str  # a stable id such as domain:academic
    label: str  # words for a person
    state: NodeState
    elapsed_ms: int | None = None
    attempt: int | None = None
    detail: str | None = None
    ok: bool | None = None  # for a check or a repair: did it come out right


class RunEvents:
    """A thread-safe event log per run. The SSE endpoint streams it, the UI draws it."""

    def __init__(self) -> None:
        self._events: dict[str, list[RunEvent]] = {}
        self._condition = threading.Condition()

    def emit(
        self,
        run_id: str,
        node: str,
        label: str,
        state: NodeState,
        *,
        elapsed_ms: int | None = None,
        attempt: int | None = None,
        detail: str | None = None,
        ok: bool | None = None,
    ) -> RunEvent:
        with self._condition:
            log = self._events.setdefault(run_id, [])
            event = RunEvent(
                id=len(log) + 1,
                ts=datetime.now(UTC),
                run_id=run_id,
                node=node,
                label=label,
                state=state,
                elapsed_ms=elapsed_ms,
                attempt=attempt,
                detail=detail,
                ok=ok,
            )
            log.append(event)
            self._condition.notify_all()
            return event

    def all(self, run_id: str) -> list[RunEvent]:
        with self._condition:
            return list(self._events.get(run_id, []))

    def since(self, run_id: str, after_id: int = 0) -> list[RunEvent]:
        return [e for e in self.all(run_id) if e.id > after_id]

    def wait(self, run_id: str, after_id: int, timeout: float) -> list[RunEvent]:
        """Block until there is something newer than `after_id`, or the timeout passes."""
        with self._condition:
            if not any(e.id > after_id for e in self._events.get(run_id, [])):
                self._condition.wait(timeout)
            return [e for e in self._events.get(run_id, []) if e.id > after_id]


def summarise(value: Any, depth: int = 0) -> Any:
    """A small, readable picture of a payload. The full content is covered by its hash."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
        return value if len(text) <= 160 else text[:157] + "..."
    if isinstance(value, dict):
        if depth >= 1:
            return f"<{len(value)} entries>"
        return {k: summarise(v, depth + 1) for k, v in list(value.items())[:25]}
    if isinstance(value, (list, tuple, set, frozenset)):
        return f"<{len(value)} items>"
    return f"<{type(value).__name__}>"


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Runtime:
    def __init__(
        self,
        audit: AuditSink,
        events: RunEvents,
        budget_seconds: float = 300.0,
    ) -> None:
        self.audit = audit
        self.events = events
        self.budget_seconds = budget_seconds
        self._started: dict[str, float] = {}
        self._crash_once: set[str] = set()
        self._lock = threading.Lock()

    def begin(self, run_id: str) -> None:
        with self._lock:
            self._started.setdefault(run_id, time.monotonic())

    def _check_budget(self, run_id: str) -> None:
        started = self._started.get(run_id)
        if started is not None and time.monotonic() - started > self.budget_seconds:
            raise BudgetExceeded(f"the run used more than {self.budget_seconds:.0f} seconds")

    def crash_once(self, node: str) -> None:
        """Test hook: make a node fail the first time it runs, to prove a crashed run resumes."""
        with self._lock:
            self._crash_once.add(node)

    def traced(
        self,
        node: str,
        label: str | Callable[[dict[str, Any]], str],
        *,
        node_id: Callable[[dict[str, Any]], str] | None = None,
        outcome: Callable[[dict[str, Any]], bool] | None = None,
        detail: Callable[[dict[str, Any]], str] | None = None,
    ):
        """Wrap a node: budget check, running and done events, and one audit row with inputs and outputs."""

        def decorator(fn: Callable[[dict[str, Any]], dict[str, Any]]):
            @functools.wraps(fn)
            def wrapper(state: dict[str, Any]) -> dict[str, Any]:
                run_id = state["run_id"]
                ident = node_id(state) if node_id else node
                words = label(state) if callable(label) else label
                attempt = state.get("attempts")
                self.begin(run_id)
                self.events.emit(run_id, ident, words, "running", attempt=attempt)
                started = time.monotonic()
                try:
                    self._check_budget(run_id)
                    with self._lock:
                        crash = node in self._crash_once
                        self._crash_once.discard(node)
                    if crash:
                        raise RuntimeError(f"{node} stopped unexpectedly (injected for a test)")
                    update = fn(state)
                except Exception as error:
                    elapsed = int((time.monotonic() - started) * 1000)
                    self.events.emit(
                        run_id, ident, words, "failed", elapsed_ms=elapsed, detail=str(error)
                    )
                    self.audit.append(
                        actor_type="agent",
                        actor_id=ident,
                        action="node.failed",
                        run_id=run_id,
                        inputs={
                            "keys": sorted(state),
                            "digest": digest({k: v for k, v in state.items() if k != "facts"}),
                        },
                        outputs={"error": str(error), "error_type": type(error).__name__},
                    )
                    raise
                elapsed = int((time.monotonic() - started) * 1000)
                self.events.emit(
                    run_id,
                    ident,
                    words,
                    "done",
                    elapsed_ms=elapsed,
                    attempt=attempt,
                    detail=detail(update) if detail else None,
                    ok=outcome(update) if outcome else None,
                )
                self.audit.append(
                    actor_type="agent",
                    actor_id=ident,
                    action="node.done",
                    run_id=run_id,
                    inputs={
                        "keys": sorted(state),
                        "digest": digest({k: v for k, v in state.items() if k != "facts"}),
                    },
                    outputs={
                        "summary": summarise(update),
                        "digest": digest(update),
                        "elapsed_ms": elapsed,
                    },
                )
                return update

            return wrapper

        return decorator
