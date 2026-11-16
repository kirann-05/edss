"""
Lab 9 - grounding: every candidate must carry an evidence record; an
ungrounded item is rejected, not kept.

Lab 10 - the acceptance gate is a hard stop; on failure, diagnose the
exact failing constraint and hand it back to the Coordinator's bounded
regenerate loop -- never rebuild the whole report over one bad figure.

Lab 11 - this IS the acceptance suite: `build(plan)` (see graph.py) must
show an all-passing `ValidationReport` before anything reaches the human
gate.

    function ValidationAgent.validate(ctx, plan):
        checks = [
          ('every figure cites its source', test_0(ctx, plan)),
          ('assumptions are stated explicitly', test_1(ctx, plan)),
          ('each option lists its risks and trade-offs', test_2(ctx, plan)),
          ('no action is taken without leadership approval', test_3(ctx, plan)),
        ]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class ValidationReport:
    passed: bool
    failing: List[str]
    diagnosis: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"passed": self.passed, "failing": self.failing, "diagnosis": self.diagnosis}


# -- individual checks -------------------------------------------------------

def _check_every_figure_cites_source(ctx, plan) -> Tuple[bool, str]:
    missing = [d for d, r in ctx.domain_results.items() if not r.get("evidence", {}).get("source_system")]
    kpi_ev = (ctx.kpi_result or {}).get("evidence", {})
    if not kpi_ev.get("source_system"):
        missing.append("kpi_synthesis")
    ok = not missing
    return ok, ("all domain and KPI figures cite a source_system" if ok
                else f"missing source citation for: {missing}")


def _check_assumptions_stated(ctx, plan) -> Tuple[bool, str]:
    assumptions = (ctx.report or {}).get("assumptions", [])
    ok = len(assumptions) >= 1
    return ok, (f"{len(assumptions)} assumption(s) stated explicitly" if ok
                else "no assumptions section found in the report")


def _check_options_have_risks(ctx, plan) -> Tuple[bool, str]:
    options = (ctx.report or {}).get("options", [])
    bad = [o.get("issue", "?") for o in options
           if not (o.get("option_a", {}).get("risks") and o.get("option_b", {}).get("risks"))]
    ok = not bad
    return ok, ("every decision option lists risks for each alternative" if ok
                else f"option(s) missing risks/trade-offs: {bad}")


def _check_no_action_without_approval(ctx, plan) -> Tuple[bool, str]:
    # At validation time (pre-human-gate) nothing should be marked
    # 'published' yet -- that only happens after governance.publish().
    ok = ctx.approval is None or ctx.approval.get("status") != "published_without_approval"
    return ok, ("no publish action has occurred prior to human approval" if ok
                else "VIOLATION: a publish action occurred before human approval")


CHECKS: List[Tuple[str, Callable]] = [
    ("every figure cites its source", _check_every_figure_cites_source),
    ("assumptions are stated explicitly", _check_assumptions_stated),
    ("each option lists its risks and trade-offs", _check_options_have_risks),
    ("no action is taken without leadership approval", _check_no_action_without_approval),
]


class ValidationAgent:
    """The hard gate. Runs every check; on failure, returns which named
    checks failed and a plain-language diagnosis for each, so the
    Coordinator's self-healing loop (Lab 10) can regenerate just the
    offending part."""

    @staticmethod
    def validate(ctx, plan) -> ValidationReport:
        failing = []
        diagnosis = {}
        for label, check_fn in CHECKS:
            ok, explanation = check_fn(ctx, plan)
            diagnosis[label] = explanation
            if not ok:
                failing.append(label)
        return ValidationReport(passed=not failing, failing=failing, diagnosis=diagnosis)


# Map a failing check to which agent's step should be re-run to fix it
# (Lab 10: "regenerate only the failing part").
FAILING_CHECK_TO_AGENT = {
    "every figure cites its source": "domain_or_kpi_agents",
    "assumptions are stated explicitly": "report_agent",
    "each option lists its risks and trade-offs": "report_agent",
    "no action is taken without leadership approval": "governance",
}
