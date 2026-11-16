"""
Lab 1 - the agent loop (clarify -> plan -> revise), hardened in Lab 6
into a governed runtime controller with budgets, checkpoints and an
audit log; Lab 10 adds the bounded self-healing regenerate loop.

The Coordinator is the "apniLeap AURA Coordinator" node (navy in the
book's node graph): it owns run-state, the locked plan, budgets and the
audit log, and drives every specialist agent -- no agent talks to
another agent directly, or bypasses it to reach data or the human gate.
"""

from __future__ import annotations

import datetime as _dt
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from eds.memory import RunState
from eds.skills import Plan, plan_skill


DEFAULT_CLARIFYING_QUESTIONS = [
    "Which review cycle is this for (e.g. Q1 FY26, NAAC snapshot)?",
    "Which domains should be included (academic / research / placement / finance, or all)?",
]


class RegenerateBudgetExhausted(RuntimeError):
    pass


@dataclass
class AuditEntry:
    ts: str
    run_id: str
    actor: str
    intent: str
    action: str
    result_summary: str


class AuditLog:
    """Append-only audit trail. Every consequential step is logged with
    what was intended, what was done, and a summary of the result --
    not just that a message passed between agents."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.entries: List[AuditEntry] = []

    def log(self, run_id: str, actor: str, intent: str, action: str, result_summary: str) -> None:
        entry = AuditEntry(
            ts=_dt.datetime.utcnow().isoformat(),
            run_id=run_id,
            actor=actor,
            intent=intent,
            action=action,
            result_summary=result_summary,
        )
        self.entries.append(entry)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.__dict__) + "\n")

    def as_list(self) -> List[Dict[str, Any]]:
        return [e.__dict__ for e in self.entries]


@dataclass
class RunContext:
    """The shared, mutable run-context every agent's `.step(ctx, plan)`
    reads from and writes to. Isolated per run; checkpointed by the
    Coordinator/Runtime so a crashed run can resume."""

    run_id: str
    plan: Plan
    state: RunState
    domain_results: Dict[str, Any] = field(default_factory=dict)
    kpi_result: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    validation_report: Optional[Dict[str, Any]] = None
    approval: Optional[Dict[str, Any]] = None
    attempts: int = 0
    log: List[str] = field(default_factory=list)

    def note(self, msg: str) -> None:
        self.log.append(msg)


class Coordinator:
    """
    Lab 1: clarify -> plan -> revise loop.
    Lab 6: wraps the loop with a budget, approval gates and checkpointing.
    Lab 10: bounded regenerate loop over a single failing agent's output.
    """

    def __init__(self, audit: Optional[AuditLog] = None, checkpoint_dir: Optional[Path] = None,
                 max_regenerate_attempts: int = 3):
        self.audit = audit or AuditLog()
        self.checkpoint_dir = checkpoint_dir
        self.max_regenerate_attempts = max_regenerate_attempts
        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # -- Lab 1: clarify / plan / revise ------------------------------------
    @staticmethod
    def clarify(user_request: Dict[str, Any],
                questioner: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
        """Ask until inputs are complete. In an unattended/batch run,
        `questioner` is None and sensible defaults fill any gaps (this
        mirrors the book's requirement that the loop *asks* -- here we
        make the fallback explicit rather than silently guessing)."""
        req = dict(user_request)
        missing = [q for q, key in zip(DEFAULT_CLARIFYING_QUESTIONS, ["review_cycle", "domains"])
                   if key not in req or not req[key]]
        for q in missing:
            if questioner:
                key = "review_cycle" if q == DEFAULT_CLARIFYING_QUESTIONS[0] else "domains"
                req[key] = questioner(q)
            # else: leave the gap for plan_skill()'s defaults to fill.
        req["_clarifying_questions_asked"] = missing
        return req

    def build_plan(self, request: Dict[str, Any]) -> Plan:
        """propose_plan(req) -> locked Plan. `while user.wants_changes:
        revise` is available via `revise_plan` for interactive use; batch
        runs accept the first locked plan."""
        return plan_skill(request)

    @staticmethod
    def revise_plan(plan: Plan, feedback: Dict[str, Any]) -> Plan:
        merged = plan.as_dict()
        merged.update(feedback)
        return plan_skill(merged)

    # -- run lifecycle -------------------------------------------------------
    def new_run(self, request: Dict[str, Any]) -> RunContext:
        run_id = str(uuid.uuid4())[:8]
        plan = self.build_plan(request)
        ctx = RunContext(run_id=run_id, plan=plan, state=RunState(request=request))
        self.audit.log(run_id, "Coordinator", "start run", "new_run",
                        f"locked plan for '{plan.review_cycle}' covering {list(plan.domains)}")
        self.checkpoint(ctx)
        return ctx

    def checkpoint(self, ctx: RunContext) -> None:
        if not self.checkpoint_dir:
            return
        path = self.checkpoint_dir / f"{ctx.run_id}.json"
        snapshot = {
            "run_id": ctx.run_id,
            "plan": ctx.plan.as_dict(),
            "domain_results": ctx.domain_results,
            "kpi_result": ctx.kpi_result,
            "report": ctx.report,
            "validation_report": ctx.validation_report,
            "approval": ctx.approval,
            "attempts": ctx.attempts,
            "log": ctx.log,
        }
        path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    def resume(self, run_id: str) -> Dict[str, Any]:
        if not self.checkpoint_dir:
            raise RuntimeError("no checkpoint_dir configured")
        path = self.checkpoint_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"no checkpoint for run {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    # -- Lab 10: bounded self-healing regenerate loop ------------------------
    def regenerate(self, ctx: RunContext, failing_agent_step: Callable[[RunContext], RunContext],
                    failing_names: List[str]) -> RunContext:
        ctx.attempts += 1
        if ctx.attempts > self.max_regenerate_attempts:
            raise RegenerateBudgetExhausted(
                f"run {ctx.run_id}: exhausted {self.max_regenerate_attempts} regenerate attempts "
                f"on failing checks {failing_names}"
            )
        self.audit.log(ctx.run_id, "Coordinator", "self-heal",
                        f"regenerate attempt {ctx.attempts}", f"targeting failing checks: {failing_names}")
        ctx = failing_agent_step(ctx)
        self.checkpoint(ctx)
        return ctx
