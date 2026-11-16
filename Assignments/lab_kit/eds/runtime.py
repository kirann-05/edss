"""
Lab 6 - Runtime: binds skills + tools + memory + connector behind the
agent loop, enforcing a budget and an approval gate, and logging every
step to the audit trail.

    run = Runtime(budget=B, gates=['publish'])
    for step in agent.loop():
        audit.log(step.intent, step.action, step.result)
        if step.risky: wait_for_approval(step)
        checkpoint(run.state)

This is the backbone Lab 7 (node graph), Lab 8 (parallel swarm), Lab 10
(self-healing) and Lab 12 (governance) all plug into -- and what
Lab 14's capstone deploys as the whole system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from eds.connector import Connector
from eds.coordinator import Coordinator, AuditLog, RunContext
from eds.graph import GraphRunner
from eds.governance import Governance
from eds.validation import ValidationReport


GATED_ACTIONS = {"publish"}  # actions in this set require a passed HumanGate.review() first


@dataclass
class RuntimeResult:
    ctx: RunContext
    validation: ValidationReport
    budget_used: int
    budget: int

    def within_budget(self) -> bool:
        return self.budget_used <= self.budget


class Runtime:
    """The governed runtime controller (Lab 6), extended with the graph
    (Lab 7/8) and governance (Lab 12) it wraps for the capstone."""

    def __init__(self, connector: Connector, budget: int = 20,
                 gates: Optional[List[str]] = None,
                 checkpoint_dir: Optional[Path] = None,
                 audit_path: Optional[Path] = None,
                 storage_dir: Optional[Path] = None,
                 kpi_agent=None, report_agent=None):
        self.connector = connector
        self.budget = budget
        self.gates = set(gates or GATED_ACTIONS)
        self.audit = AuditLog(path=audit_path)
        self.coordinator = Coordinator(audit=self.audit, checkpoint_dir=checkpoint_dir)
        self.graph = GraphRunner(self.coordinator, connector, kpi_agent=kpi_agent, report_agent=report_agent)
        self.governance = Governance(storage_dir=storage_dir)
        self._budget_used = 0

    def _spend(self, n: int = 1) -> None:
        self._budget_used += n
        if self._budget_used > self.budget:
            raise RuntimeError(
                f"Runtime budget exhausted ({self._budget_used}/{self.budget} steps). "
                f"Raise `budget` or narrow the plan's scope."
            )

    def run_to_draft(self, request: Dict[str, Any]) -> RuntimeResult:
        """Runs clarify -> plan -> parallel domain aggregation -> KPI
        synthesis -> report generation -> validation (with bounded
        self-healing). Stops BEFORE the human gate -- publishing is a
        separate, explicit call that always requires a `Decision`."""
        clarified = self.coordinator.clarify(request)
        self._spend()
        ctx = self.coordinator.new_run(clarified)
        self._spend()

        ctx = self.graph.build_draft(ctx)
        self._spend(4)  # four domain agents, run in parallel but budgeted as 4 units of work

        report = self.graph.validate_with_self_healing(ctx)
        self._spend(ctx.attempts)

        return RuntimeResult(ctx=ctx, validation=report, budget_used=self._budget_used, budget=self.budget)

    def publish(self, ctx: RunContext, decision, action: str = "publish"):
        if action in self.gates and not decision.approved:
            raise PermissionError(
                f"Action '{action}' is gated and requires an approved Decision "
                f"(got decision='{decision.decision}')."
            )
        version = self.governance.publish(ctx.report, decision, run_id=ctx.run_id)
        self.audit.log(ctx.run_id, decision.actor, "publish",
                        f"governed publish v{version.version}",
                        f"approved by {decision.actor} ({decision.role})")
        self.governance.record_metric("validation_attempts", ctx.attempts, ctx.run_id)
        self.governance.record_metric("kpis_below_target",
                                       len((ctx.kpi_result or {}).get("below_target", [])), ctx.run_id)
        return version
